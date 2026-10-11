"""Offline wire-contract tests; no Slack SDK dependency or network access."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import binder_publication as publication
from test_publication import record


class RequestContractTests(unittest.TestCase):
    token = "offline-placeholder"
    upload_url = "https://files.slack.com/upload/private-fixture"

    def setUp(self):
        self.env = patch.dict(os.environ, {"SLACK_BOT_TOKEN": self.token, "GH_TOKEN": self.token})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.transport = patch.object(publication.urllib.request, "build_opener")
        self.opener = self.transport.start().return_value
        self.addCleanup(self.transport.stop)
        self.response = self.opener.open.return_value.__enter__.return_value
        self.response.read.return_value = b'{"ok":true}'

    def requests(self):
        return [call.args[0] for call in self.opener.open.call_args_list]

    def test_ticket_matches_sdk_3450_form_contract_and_preserves_pdf_bytes(self):
        # Synthetic bytes with the retained production artifact's exact length;
        # no generated PDF or SDK package is committed or needed in CI.
        pdf = b"%PDF-" + b"a" * (1916014 - 5)
        ticket = {"ok": True, "upload_url": self.upload_url, "file_id": "F1"}
        self.response.read.side_effect = [json.dumps(ticket).encode(), b""]
        self.assertEqual(publication.Services().upload(pdf), "F1")
        allocation, upload = self.requests()
        self.assertEqual(allocation.get_method(), "POST")
        self.assertEqual(allocation.full_url, "https://slack.com/api/files.getUploadURLExternal")
        self.assertEqual(allocation.get_header("Content-type"), "application/x-www-form-urlencoded")
        # Independently captured from slack_sdk 3.45.0 with its HTTP transport mocked.
        self.assertEqual(allocation.data,
                         b"filename=aquiloop-binder-mosquitofish-draft.pdf&length=1916014")
        self.assertEqual(parse_qs(allocation.data.decode()),
                         {"filename": [publication.PDF_NAME], "length": [str(len(pdf))]})
        self.assertEqual(allocation.get_header("Authorization"), "Bearer " + self.token)
        self.assertNotIn(self.token.encode(), allocation.data)
        self.assertNotIn(self.token, allocation.full_url)
        self.assertEqual(upload.full_url, self.upload_url)
        self.assertEqual(upload.get_header("Content-type"), "application/octet-stream")
        self.assertIs(upload.data, pdf)
        self.assertIsNone(upload.get_header("Authorization"))
        self.assertTrue(all(call.kwargs["timeout"] == 45 for call in self.opener.open.call_args_list))

    def test_ticket_length_counts_bytes(self):
        pdf = "%PDF-é".encode("utf-8")
        self.response.read.side_effect = [json.dumps({"ok": True, "upload_url": self.upload_url,
                                                    "file_id": "F1"}).encode(), b""]
        publication.Services().upload(pdf)
        data = parse_qs(self.requests()[0].data.decode())
        self.assertEqual(data["length"], ["7"])

    def test_other_json_requests_are_unchanged(self):
        api = publication.Services()
        api.slack("auth.test", {})
        api.complete(dict(record(), file_id="F1"))
        api.github("contents/publication.json", "PUT", {"content": "fixture"})
        auth, completion, github = self.requests()
        for request in (auth, completion, github):
            self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(json.loads(auth.data), {})
        files = json.loads(completion.data)["files"]
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["id"], "F1")
        self.assertIsInstance(files[0]["title"], str)
        self.assertEqual(json.loads(completion.data)["channel_id"], publication.CHANNEL)
        self.assertEqual(github.get_method(), "PUT")
        self.assertEqual(json.loads(github.data), {"content": "fixture"})

    def test_files_info_keeps_get_query_without_body(self):
        publication.Services().slack("files.info", {"file": "F1"})
        request = self.requests()[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.data)
        self.assertEqual(parse_qs(urlparse(request.full_url).query), {"file": ["F1"]})

    def test_ticket_rejection_stops_without_fallback_or_checkpoint(self):
        poison = "xoxb-fixture person@example.test\n::warning::injected " + self.upload_url
        self.response.read.side_effect = [json.dumps({"ok": True, "team_id": publication.TEAM}).encode(),
                                          json.dumps({"ok": False, "error": "invalid_arguments",
                                                      "response_metadata": poison}).encode()]
        api = publication.Services()
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(api, "load", return_value=None), patch.object(api, "save") as save, \
                patch.object(api, "complete") as complete, \
                patch.object(publication, "main", side_effect=lambda: publication.publish(api, record(), b"%PDF-test")), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(publication.cli(), 1)
        self.assertEqual(len(self.requests()), 2)  # auth.test + one ticket request
        save.assert_not_called()
        complete.assert_not_called()
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(len(stderr.getvalue().splitlines()), 1)
        self.assertIn("files.getUploadURLExternal failed (invalid_arguments)", stderr.getvalue())
        for marker in ("xoxb-", "person@", "::warning::", "https://", "Traceback"):
            self.assertNotIn(marker, stderr.getvalue())
        self.assertLess(len(stderr.getvalue()), 300)


if __name__ == "__main__":
    unittest.main()
