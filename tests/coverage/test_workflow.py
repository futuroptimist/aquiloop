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
        self.report, uploads = self.workflow.split("  upload_trusted:\n", 1)
        self.trusted, self.fork = uploads.split("  upload_fork:\n", 1)

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
        for upload in (self.trusted, self.fork):
            self.assertIn("    continue-on-error: true", upload)
            self.assertIn("    needs: report", upload)
            self.assertIn("needs.report.outputs.report_ready == 'true'", upload)
        self.assertNotIn("pull_request_target", self.workflow)
        self.assertNotIn("secrets.", self.workflow)
        self.assertNotIn("CODECOV_TOKEN", self.workflow)
        self.assertEqual(self.workflow.count(": write"), 1)
        self.assertNotIn("id-token:", self.report)
        self.assertNotIn("id-token:", self.fork)
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

    def test_trusted_oidc_and_public_fork_upload_conditions_are_disjoint(self):
        shared = (
            "needs.report.outputs.report_ready == 'true' && "
            "github.repository == 'futuroptimist/aquiloop' && "
        )
        actor = "github.actor != 'dependabot[bot]'"
        author = "github.event.pull_request.user.login != 'dependabot[bot]'"
        head = "github.event.pull_request.head.repo.full_name"
        trusted = (
            shared + actor + " && !endsWith(github.actor, '[bot]') && "
            "((github.event_name == 'push' && github.ref == 'refs/heads/main') || "
            "(github.event_name == 'pull_request' && "
            f"{head} == github.repository && {author} && "
            "github.event.pull_request.user.type == 'User'))"
        )
        fork = (
            shared + "github.event_name == 'pull_request' && "
            "toJSON(github.event.repository.private) == 'false' && "
            f"{head} != '' && {head} != github.repository && {actor} && {author}"
        )
        for segment, expected in ((self.trusted, trusted), (self.fork, fork)):
            condition = segment.split("    if: >-\n", 1)[1].split("    permissions:", 1)[0]
            condition = " ".join(condition.split())
            self.assertEqual(condition, "${{ " + expected + " }}")

    def test_only_isolated_trusted_upload_has_oidc_and_no_user_code_runs(self):
        self.assertIn("permissions:\n      contents: read\n      id-token: write", self.trusted)
        self.assertIn("permissions:\n      contents: read\n    runs-on:", self.fork)
        self.assertEqual(self.workflow.count("use_oidc: true"), 1)
        self.assertIn("use_oidc: true", self.trusted)
        self.assertNotIn("use_oidc", self.fork)
        for upload in (self.trusted, self.fork):
            self.assertIn("persist-credentials: false", upload)
            self.assertIn("fetch-depth: 0", upload)
            self.assertIn("name: aquiloop-python-coverage", upload)
            self.assertIn("files: ${{ runner.temp }}/aquiloop-coverage/python.xml", upload)
            self.assertIn("disable_search: true", upload)
            self.assertIn("codecov/codecov-action@0fb7174895f61a3b6b78fc075e0cd60383518dac", upload)
            self.assertEqual(upload.count("        run:"), 1)
            self.assertIn("run: echo '::warning::Advisory Codecov upload failed.", upload)


if __name__ == "__main__":
    unittest.main()
