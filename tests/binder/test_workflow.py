from __future__ import annotations

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "binder.yml"


class BinderWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_triggers_permissions_and_immutable_actions(self):
        self.assertRegex(self.workflow, r"(?m)^  pull_request:$")
        self.assertRegex(self.workflow, r"(?m)^  push:$")
        self.assertIn("branches: [main]", self.workflow)
        self.assertRegex(self.workflow, r"(?m)^  workflow_dispatch: \{\}$")
        self.assertRegex(self.workflow, r"(?m)^permissions:\n  contents: read$")
        actions = re.findall(r"(?m)^\s*uses: (\S+)", self.workflow)
        action_names = {action.split("@", 1)[0] for action in actions}
        for required_action in (
            "actions/checkout",
            "actions/setup-python",
            "actions/upload-artifact",
        ):
            self.assertIn(required_action, action_names)
        for action in actions:
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")

    def test_pinned_tools_draft_build_and_single_artifact(self):
        for expected in (
            "runs-on: ubuntu-24.04",
            "python-version: '3.12.13'",
            "https://snapshot.ubuntu.com/ubuntu/20260828T000000Z/",
            "texlive-binaries=2023.20230311.66589-9build3",
            'PIL.__version__ == "12.3.0"',
            'pypdf.__version__ == "6.18.1"',
            'test "$(python --version 2>&1)" = "Python 3.12.13"',
            "LuaHBTeX, Version 1.17.0",
            "pdfinfo version 24.02.0",
            "pdftoppm version 24.02.0",
            "pdfinfo -v",
            "pdftoppm -v",
            "dpkg-query -W",
            "python -m unittest discover -s tests/binder -v",
            "--manifest binder/manifest.yaml --mode draft",
            "pdfinfo -box build/binder/aquiloop-binder-draft.pdf",
            "name: aquiloop-binder-draft",
            "path: build/binder/aquiloop-binder-draft.pdf",
        ):
            self.assertIn(expected, self.workflow)
        self.assertEqual(self.workflow.count("actions/upload-artifact@"), 1)
        self.assertEqual(self.workflow.count("path: build/binder/aquiloop-binder-draft.pdf"), 1)
        for package in (
            "fonts-texgyre",
            "poppler-utils",
            "texlive-binaries",
            "texlive-fonts-recommended",
            "texlive-latex-base",
            "texlive-luatex",
            "texlive-pictures",
        ):
            self.assertRegex(self.workflow, rf"(?m)^\s+{package}=\S+")

    def _run_regression_gate(self, output: str, exit_code: int = 0):
        marker = "      - name: Run complete binder regression suite\n        run: |\n"
        script = self.workflow.split(marker, 1)[1].split("\n      - name:", 1)[0]
        script = textwrap.dedent(script)
        with tempfile.TemporaryDirectory() as directory:
            fake_bin = Path(directory) / "bin"
            fake_bin.mkdir()
            fake_python = fake_bin / "python"
            fake_python.write_text(
                "#!/bin/sh\nprintf '%s' \"$FAKE_UNITTEST_OUTPUT\"\n"
                'exit "$FAKE_UNITTEST_EXIT"\n',
                encoding="utf-8",
            )
            fake_python.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                {
                    "FAKE_UNITTEST_OUTPUT": output,
                    "FAKE_UNITTEST_EXIT": str(exit_code),
                    "PATH": f"{fake_bin}{os.pathsep}{environment['PATH']}",
                }
            )
            return subprocess.run(
                ["bash", "-c", script],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_regression_gate_accepts_any_positive_passing_test_count(self):
        result = self._run_regression_gate("Ran 42 tests in 0.123s\n\nOK\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_regression_gate_rejects_unsuccessful_or_empty_suites(self):
        cases = {
            "failure": ("Ran 42 tests in 0.123s\n\nFAILED (failures=1)\n", 1),
            "error": ("Ran 42 tests in 0.123s\n\nFAILED (errors=1)\n", 1),
            "skip": ("Ran 42 tests in 0.123s\n\nOK (skipped=1)\n", 0),
            "empty": ("Ran 0 tests in 0.000s\n\nOK\n", 0),
        }
        for name, (output, exit_code) in cases.items():
            with self.subTest(name=name):
                result = self._run_regression_gate(output, exit_code)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
