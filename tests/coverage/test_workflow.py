"""Offline guards for the advisory Python coverage workflow."""

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/python-patch-coverage.yml"


class AdvisoryCoverageTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text()
        self.report, self.upload = self.workflow.split("  upload:\n", 1)

    def extract_run(self, segment, step):
        section = segment.split(f"      - name: {step}\n", 1)[1]
        return textwrap.dedent(section.split("        run: |\n", 1)[1].split("\n      - ", 1)[0])

    def test_advisory_jobs_do_not_change_binder_validation_or_publication(self):
        binder = (ROOT / ".github/workflows/binder.yml").read_text()
        self.assertIn("python -m unittest discover -s tests/publication -v", binder)
        self.assertIn("python -m unittest discover -s tests/binder -v", binder)
        self.assertIn("publish:\n    name: Publish changed binder to Slack\n    needs: build", binder)
        self.assertNotIn("codecov", binder.lower())
        self.assertIn("    continue-on-error: true", self.report)
        self.assertIn("    continue-on-error: true", self.upload)
        self.assertIn("needs.report.outputs.report_ready == 'true'", self.upload)
        self.assertNotIn("secrets.", self.report)
        self.assertNotIn("pull_request_target", self.workflow)
        self.assertNotIn("id-token:", self.workflow)
        self.assertNotIn(": write", self.workflow)
        config = (ROOT / "codecov.yml").read_text()
        for expected in ("project: false", "informational: true", "only_pulls: true", "- scripts/"):
            self.assertIn(expected, config)

    def test_no_report_when_either_suite_fails_or_is_incomplete(self):
        script = self.extract_run(self.report, "Measure both existing regression suites")
        for publication, binder, expected in (
            ("pass", "pass", True),
            ("fail", "pass", False),
            ("pass", "fail", False),
            ("pass", "skip", False),
            ("empty", "pass", False),
        ):
            with self.subTest(publication=publication, binder=binder), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                fake_python = root / "python"
                fake_python.write_text(
                    "#!/bin/sh\n"
                    'case "$*" in\n'
                    '  *"coverage xml"*) touch "$REPORT_MARKER"; exit $? ;;\n'
                    '  *tests/publication*) outcome="$PUBLICATION" ;;\n'
                    '  *tests/binder*) outcome="$BINDER" ;;\n'
                    "  *) exit 99 ;;\n"
                    "esac\n"
                    'case "$outcome" in\n'
                    "  pass) printf 'Ran 2 tests in 0.001s\\nOK\\n' ;;\n"
                    "  skip) printf 'Ran 2 tests in 0.001s\\nOK (skipped=1)\\n' ;;\n"
                    "  empty) printf 'Ran 0 tests in 0.001s\\nOK\\n' ;;\n"
                    "  fail) exit 1 ;;\n"
                    "esac\n"
                )
                fake_python.chmod(0o755)
                report = root / "marker"
                result = subprocess.run(
                    ["bash", "-c", script],
                    env=dict(
                        os.environ,
                        PATH=f"{root}{os.pathsep}{os.environ['PATH']}",
                        RUNNER_TEMP=d,
                        REPORT_MARKER=str(report),
                        PUBLICATION=publication,
                        BINDER=binder,
                    ),
                    cwd=d,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode == 0, expected, result.stdout + result.stderr)
                self.assertEqual(report.exists(), expected)

    def test_upload_auth_routes(self):
        script = self.extract_run(self.upload, "Decide whether Codecov upload is configured")
        self.assertIn(
            "steps.upload.outputs.mode == 'trusted' && secrets.CODECOV_TOKEN || ''", self.upload
        )
        self.assertIn("files: build/coverage/python.xml", self.upload)
        self.assertIn("disable_search: true", self.upload)
        for event, head, token, mode in (
            ("push", "", "not-printed", "trusted"),
            ("pull_request", "futuroptimist/aquiloop", "not-printed", "trusted"),
            ("pull_request", "contributor/aquiloop", "", "fork"),
            ("pull_request", "contributor/aquiloop", "not-printed", "fork"),
            ("pull_request", "futuroptimist/aquiloop", "", ""),
            ("push", "", "", ""),
        ):
            with self.subTest(event=event, head=head, mode=mode), tempfile.TemporaryDirectory() as d:
                output = Path(d) / "output"
                output.touch()
                result = subprocess.run(
                    ["bash", "-c", script],
                    env=dict(
                        os.environ,
                        EVENT_NAME=event,
                        HEAD_REPOSITORY=head,
                        UPSTREAM_REPOSITORY="futuroptimist/aquiloop",
                        CODECOV_TOKEN=token,
                        GITHUB_OUTPUT=str(output),
                    ),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertEqual(output.read_text(), f"mode={mode}\n" if mode else "")
                self.assertNotIn("not-printed", result.stdout + result.stderr)
                if not mode:
                    self.assertIn("Codecov upload skipped", result.stdout)


if __name__ == "__main__":
    unittest.main()
