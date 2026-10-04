"""Regression coverage for evidence boundaries and opt-in v2 assembly."""
import copy
import json
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import binder_evidence as evidence
import build_binder as builder


class CompanionEvidenceTests(unittest.TestCase):
    def test_all_five_research_collections(self):
        for entry, _ in builder.EXPECTED_MANIFEST[:-1]:
            with self.subTest(entry=entry):
                self.assertTrue(evidence.load_companions(ROOT, entry)["claims"])

    def test_invalid_claims_are_rejected(self):
        data = evidence.load_companions(ROOT, "pothos")
        original = data["claims"]["pothos#preferred-temperature"]
        changes = [
            lambda c: c.update(description="second payload"),
            lambda c: c["quantity"].update(minimum=100),
            lambda c: c["quantity"].update(maximum=Decimal("Infinity")),
            lambda c: c["quantity"].update(minimum=True),
            lambda c: c["provenance"].update(source_refs=["MISSING"]),
            lambda c: c.update(evidence_category="proposed"),
            lambda c: c.update(evidence_category="observed"),
            lambda c: c.update(evidence_category="unknown"),
            lambda c: c.update(applicable_taxon=""),
        ]
        for mutate in changes:
            c = copy.deepcopy(original)
            mutate(c)
            with self.assertRaises(ValueError):
                evidence.validate_claim(c, data["sources"])

    def test_decimal_recipe_and_conversion(self):
        data = evidence.load_companions(ROOT, "sedum-loves-fire")
        c = copy.deepcopy(data["claims"]["sedum-loves-fire#established-substrate-recipe"])
        evidence.validate_claim(c, data["sources"])
        c["recipe"]["components"][0]["percent_by_volume"] += Decimal("0.0000000001")
        with self.assertRaises(ValueError):
            evidence.validate_claim(c, data["sources"])

    def test_unknown_cannot_have_citations_or_numbers(self):
        data = evidence.load_companions(ROOT, "pothos")
        c = copy.deepcopy(data["claims"]["pothos#lifespan"])
        c["provenance"]["source_refs"] = ["POT-WISC"]
        with self.assertRaises(ValueError):
            evidence.validate_claim(c, data["sources"])
        c["provenance"] = {}
        c["quantity"]["value"] = 0
        with self.assertRaises(ValueError):
            evidence.validate_claim(c, data["sources"])

    def test_canonical_sixteen_page_manifest(self):
        entries = builder.load_manifest(ROOT / "binder/manifest-v2.yaml")
        self.assertEqual(tuple((i["id"], i["kind"]) for i in entries), builder.EXPECTED_EXPANDED_MANIFEST)
        self.assertEqual(len(entries), 16)
        self.assertEqual(len(builder.load_manifest(ROOT / "binder/manifest.yaml")), 6)

    def test_v2_rejects_reorder_duplicate_missing_and_budget(self):
        original = json.loads((ROOT / "binder/manifest-v2.yaml").read_text())
        mutations = [lambda a: a.reverse(), lambda a: a.pop(),
                     lambda a: a.append(a[0]), lambda a: a[1].update(page_budget=2),
                     lambda a: a[1].update(kind="profile")]
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / "binder/manifest-v2.yaml"
                path.parent.mkdir()
                doc = copy.deepcopy(original)
                mutate(doc["entries"])
                path.write_text(json.dumps(doc))
                with mock.patch.object(builder, "ROOT", root), self.assertRaises(ValueError):
                    builder.load_manifest(path)

    def test_companions_reject_final_mode_and_path_traversal(self):
        for entry, kind, mode in [("pothos", "numbers", "final"), ("../pothos", "numbers", "draft")]:
            with self.assertRaises(ValueError):
                builder.compile_companion(entry, kind, mode, Path("unused.pdf"))

    def test_shared_context_and_nested_aquatic_references(self):
        context = "pacifica-ca-coastal-context-v1#zip-94044-majority-hardiness-zone"
        self.assertIn(context, evidence.load_companions(ROOT, "pothos")["valid_refs"])
        original_read = evidence.read
        def mutated_read(path):
            d = original_read(path)
            if path.name == "numbers.yaml" and path.parent.name == "aquarium-hornwort":
                d["aquatic_setup"]["placement"]["claim_ref"] = "aquarium-hornwort#missing"
            return d
        with mock.patch.object(evidence, "read", side_effect=mutated_read), self.assertRaisesRegex(ValueError, "unresolved claim"):
            evidence.load_companions(ROOT, "aquarium-hornwort")

    def test_layout_accepts_context_reference_but_rejects_unvalidated_images(self):
        context = "pacifica-ca-coastal-context-v1#zip-94044-majority-hardiness-zone"
        original = Path.read_text
        page = "% claim-ref: " + context + "\n"
        def read_page(path, *args, **kwargs):
            return page if path.name == "numbers.tex" else original(path, *args, **kwargs)
        with mock.patch.object(Path, "read_text", read_page), mock.patch.object(builder, "compile_entry") as compile_page:
            builder.compile_companion("pothos", "numbers", "draft", Path("unused.pdf"))
            compile_page.assert_called_once()
            page += "% binder-placement hero ignored-asset; bypass must fail\n"
            with self.assertRaisesRegex(ValueError, "photograph placement is not supported"):
                builder.compile_companion("pothos", "numbers", "draft", Path("unused.pdf"))


if __name__ == "__main__":
    unittest.main()
