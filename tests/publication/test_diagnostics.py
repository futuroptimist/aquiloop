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
from test_publication import FakeServices, record


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

    def test_signed_upload_http_errors_keep_safe_categories(self):
        for status, code in ((429, "ratelimited"), (403, "http_error"), (500, "http_error")):
            api = publication.Services()
            error = urllib.error.HTTPError(self.poison, status, self.poison,
                                           {"Retry-After": self.poison}, io.BytesIO(self.poison.encode()))
            with patch.object(api, "slack", return_value={
                    "upload_url": "https://files.slack.com/private", "file_id": "F1"}), \
                    patch.object(publication.urllib.request, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                output = self.capture(lambda: api.upload(b"%PDF-test"))
                opener.return_value.open.assert_called_once()
            self.assertIn(f"upload_bytes failed ({code})", output)

    def test_safe_errors_only_emit_fixed_messages(self):
        for code, message in publication.SAFE_ERRORS.items():
            output = self.capture(lambda: self.raise_error(publication.SafeError(code)))
            self.assertEqual(output, f"::error::{message}\n")
        for code in (self.poison, [], {}, None):
            output = self.capture(lambda: self.raise_error(publication.SafeError(code)))
            self.assertIn(publication.SAFE_ERRORS["unexpected"], output)

    def test_owner_actionable_publication_failures_reach_annotation(self):
        for code in ("workspace", "checkpoint", "history"):
            api = FakeServices()
            if code == "workspace":
                api.team = self.poison
            elif code == "checkpoint":
                api.state = dict(record(), status=self.poison, file_id=self.poison)
            else:
                api.state = dict(record(), status="published", file_id="F1")
                api.status = self.poison
            output = self.capture(lambda: publication.publish(api, record(), b"%PDF-test"))
            self.assertIn(publication.SAFE_ERRORS[code], output)
            self.assertEqual((api.uploads, api.posts), (0, 0))

    def test_trust_failure_remains_actionable_without_network(self):
        main = publication.main
        with patch.object(sys, "argv", ["publisher", "publish"]), \
                patch.dict(os.environ, {"GITHUB_EVENT_NAME": self.poison}, clear=True), \
                patch.object(publication, "Services") as services:
            output = self.capture(main)
        self.assertIn(publication.SAFE_ERRORS["trust"], output)
        services.assert_not_called()

    def test_manifest_failures_have_local_guidance_without_leaking(self):
        main = publication.main
        for error in (ValueError(self.poison), OSError(self.poison),
                      publication.SafeError("geometry")):
            with patch.object(sys, "argv", ["publisher", "manifest"]), \
                    patch.object(publication, "manifest", side_effect=error), \
                    patch.object(publication, "Services") as services:
                output = self.capture(main)
            expected = "geometry" if isinstance(error, publication.SafeError) else "manifest"
            self.assertIn(publication.SAFE_ERRORS[expected], output)
            self.assertNotIn("service health", output)
            self.assertNotIn("checkpoint", output)
            services.assert_not_called()

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
