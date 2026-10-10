"""Adversarial diagnostics tests: all network traffic is mocked."""
import contextlib
import io

import os
from pathlib import Path
import sys
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import binder_publication as publication


class DiagnosticsTests(unittest.TestCase):
    poison = "xoxb-secret-person@example.test\r\n::warning::injected https://files.slack.com/upload/private"

    def capture(self, action):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), \
                patch.object(publication, "main", side_effect=action):
            self.assertEqual(publication.cli(), 1)
        self.assertEqual(stdout.getvalue(), "")
        output = stderr.getvalue()
        self.assertEqual(len(output.splitlines()), 1)
        self.assertTrue(output.startswith("::error::"))
        self.assertLess(len(output), 300)
        for forbidden in (self.poison, "xoxb-", "person@", "https://", "::warning::", "Traceback"):
            self.assertNotIn(forbidden, output)
        return output

    def call_slack(self, response, method="files.getUploadURLExternal"):
        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": self.poison}), \
                patch.object(publication, "request", return_value=response):
            publication.Services().slack(method, {})

    def test_each_allowlisted_error_and_method_has_bounded_annotation(self):
        for method in publication.SLACK_METHODS:
            for code in publication.SLACK_HINTS:
                with self.subTest(method=method, code=code):
                    result = self.capture(lambda: self.call_slack(
                        {"ok": False, "error": code, "needed": self.poison,
                         "provided": self.poison, "response_metadata": self.poison}, method))
                    self.assertIn(f"Slack {method} failed ({code})", result)

    def test_unknown_and_nonstring_errors_never_echo(self):
        for code in (self.poison, "missing_scope\n" + self.poison, "a" * 100000,
                     None, [], {}, 17, True):
            with self.subTest(kind=type(code).__name__):
                result = self.capture(lambda: self.call_slack({"ok": False, "error": code}))
                self.assertIn("(api_error)", result)
        result = self.capture(lambda: self.call_slack({"ok": False, "error": "missing_scope"}, self.poison))
        self.assertIn("unknown_method", result)

    def test_malformed_response_and_unexpected_exceptions_are_safe(self):
        for response in ([], None, self.poison):
            result = self.capture(lambda: self.call_slack(response))
            self.assertIn("invalid_response", result)
        for error in (ValueError(self.poison), KeyError(self.poison), RuntimeError(self.poison)):
            self.capture(lambda: self.raise_error(error))

    @staticmethod
    def raise_error(error):
        raise error

    def test_http_transport_and_json_failures_do_not_leak(self):
        errors = [urllib.error.HTTPError(self.poison, 429, self.poison,
                                        {"Authorization": self.poison}, io.BytesIO(self.poison.encode())),
                  urllib.error.HTTPError(self.poison, 403, self.poison, {}, None),
                  urllib.error.URLError(self.poison), TimeoutError(self.poison)]
        for error, code in zip(errors, ("ratelimited", "http_error", "transport_error", "transport_error")):
            with patch.dict(os.environ, {"SLACK_BOT_TOKEN": self.poison}), \
                    patch.object(publication.urllib.request, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                result = self.capture(lambda: publication.Services().slack("files.getUploadURLExternal", {}))
                self.assertIn(f"({code})", result)
                opener.return_value.open.assert_called_once()
        for body in (self.poison.encode(), b"\xff"):
            with patch.dict(os.environ, {"SLACK_BOT_TOKEN": self.poison}), \
                    patch.object(publication.urllib.request, "build_opener") as opener:
                opener.return_value.open.return_value.__enter__.return_value.read.return_value = body
                result = self.capture(lambda: publication.Services().slack("auth.test", {}))
                self.assertIn("invalid_response", result)

    def test_upload_url_failure_is_safe(self):
        api = publication.Services()
        with patch.object(api, "slack", return_value={"upload_url": "https://files.slack.com/private", "file_id": "F1"}), \
                patch.object(publication, "request", side_effect=publication.ApiError("Transport", "uncertain")) as request:
            result = self.capture(lambda: api.upload(b"%PDF-test"))
        self.assertIn("upload_bytes failed (transport_error)", result)
        request.assert_called_once()

    def test_success_is_unchanged(self):
        with patch.object(publication, "main", return_value=None):
            self.assertEqual(publication.cli(), 0)

    def test_workflow_keeps_publication_gates(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/binder.yml").read_text()
        publish = workflow.split("\n  publish:\n", 1)[1]
        for gate in ("needs: build", "github.event_name == 'push'", "github.ref == 'refs/heads/main'",
                     "github.repository == 'futuroptimist/aquiloop'",
                     "github.event.repository.default_branch == 'main'",
                     "vars.BINDER_SLACK_PUBLISH_ENABLED == 'true'", "cancel-in-progress: false"):
            self.assertIn(gate, publish)


if __name__ == "__main__":
    unittest.main()
