from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_binder_content  # noqa: E402


class ContentWorksheetTests(unittest.TestCase):
    def test_all_research_worksheets_are_complete(self):
        self.assertEqual(validate_binder_content.validate_all(), [])

    def test_unknown_claim_source_is_rejected(self):
        real = ROOT / "binder/entries/pothos"
        with tempfile.TemporaryDirectory() as name:
            candidate = Path(name)
            for filename in ("sources.yaml", "content.yaml"):
                (candidate / filename).write_text((real / filename).read_text(), encoding="utf-8")
            content = json.loads((candidate / "content.yaml").read_text())
            content["cards"]["water"][0]["sources"] = ["missing-source"]
            (candidate / "content.yaml").write_text(json.dumps(content), encoding="utf-8")
            errors = validate_binder_content.validate_entry(candidate)
            self.assertTrue(any("unknown sources" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
