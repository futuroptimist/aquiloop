import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "binder.yml"


class BinderWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_triggers_permissions_and_immutable_actions(self):
        self.assertIn("pull_request:", self.workflow)
        self.assertRegex(self.workflow, r"push:\n    branches: \[main\]")
        self.assertIn("workflow_dispatch: {}", self.workflow)
        self.assertRegex(self.workflow, r"permissions:\n  contents: read")
        action_refs = re.findall(r"uses:\s+([^\s#]+)", self.workflow)
        self.assertEqual(len(action_refs), 3)
        self.assertTrue(all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", ref) for ref in action_refs))

    def test_pinned_tools_draft_build_and_single_artifact(self):
        for version in ("3.12.13", "12.3.0", "6.18.1", "1.17.0", "24.02.0"):
            self.assertIn(version, self.workflow)
        command = (
            "python scripts/build_binder.py --manifest binder/manifest.yaml "
            "--mode draft --output build/binder/aquiloop-binder-draft.pdf"
        )
        self.assertIn(command, self.workflow)
        self.assertEqual(self.workflow.count("actions/upload-artifact@"), 1)
        self.assertIn("name: aquiloop-care-binder-draft", self.workflow)
        self.assertIn("path: build/binder/aquiloop-binder-draft.pdf", self.workflow)


if __name__ == "__main__":
    unittest.main()
