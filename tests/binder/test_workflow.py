from __future__ import annotations

import re
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
        self.assertEqual(len(actions), 3)
        for action in actions:
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")

    def test_pinned_tools_draft_build_and_single_artifact(self):
        for expected in (
            "runs-on: ubuntu-24.04",
            "python-version: '3.12.13'",
            'PIL.__version__ == "12.3.0"',
            'pypdf.__version__ == "6.18.1"',
            "lualatex --version",
            "pdfinfo -v",
            "pdftoppm -v",
            "python -m unittest discover -s tests/binder -v",
            "--manifest binder/manifest.yaml --mode draft",
            "pdfinfo -box build/binder/aquiloop-binder-draft.pdf",
            "name: aquiloop-binder-draft",
            "path: build/binder/aquiloop-binder-draft.pdf",
        ):
            self.assertIn(expected, self.workflow)
        self.assertEqual(self.workflow.count("actions/upload-artifact@"), 1)
        self.assertEqual(self.workflow.count("path: build/binder/aquiloop-binder-draft.pdf"), 1)


if __name__ == "__main__":
    unittest.main()
