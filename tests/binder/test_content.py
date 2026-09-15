from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TERRESTRIAL = {
    "light_exposure", "soil_substrate", "water", "temperature_season",
    "feeding_maintenance", "propagation", "troubleshooting",
    "natural_history_trivia",
}
ENTRIES = {
    "sedum-loves-fire": TERRESTRIAL,
    "kalanchoe-desert": TERRESTRIAL,
    "pothos": TERRESTRIAL,
    "bird-of-paradise": TERRESTRIAL,
    "aquarium-hornwort": {
        "light", "water_parameters_temperature", "placement_anchoring_floating",
        "nutrient_context", "growth_trimming", "propagation",
        "aquarium_compatibility_troubleshooting", "natural_history_trivia",
    },
}


class ContentWorksheetTests(unittest.TestCase):
    def load(self, slug: str, filename: str) -> dict:
        # JSON is a deliberately restricted YAML subset, so stdlib validation
        # does not add a repository dependency.
        path = ROOT / "binder" / "entries" / slug / filename
        return json.loads(path.read_text(encoding="utf-8"))

    def test_source_and_content_contracts(self):
        for slug, expected_cards in ENTRIES.items():
            with self.subTest(entry=slug):
                source_doc = self.load(slug, "sources.yaml")
                content = self.load(slug, "content.yaml")
                self.assertEqual(source_doc["schema_version"], 1)
                self.assertEqual(content["schema_version"], 1)
                self.assertEqual(source_doc["entry"], slug)
                self.assertEqual(content["entry"], slug)

                sources = source_doc["sources"]
                keys = {source["key"] for source in sources}
                self.assertEqual(len(keys), len(sources))
                for source in sources:
                    for field in ("key", "authority", "title", "url", "accessed"):
                        self.assertTrue(source[field])
                    self.assertTrue(source["url"].startswith("https://"))
                    self.assertTrue(source["supports"])

                self.assertEqual(set(content["cards"]), expected_cards)
                self.assertIn("propagation", content["cards"])
                self.assertTrue(content["identity"]["status"])
                self.assertTrue(content["identity"]["decision"])
                self.assertTrue(content["identity"]["sources"])
                self.assertTrue(content["unresolved_fields"])
                self.assertTrue(content["environmental_variability"])

                cited = set(content["identity"]["sources"])
                for claims in content["cards"].values():
                    self.assertTrue(claims)
                    for claim in claims:
                        self.assertTrue(claim["claim"])
                        self.assertTrue(claim["sources"])
                        cited.update(claim["sources"])
                self.assertLessEqual(cited, keys)

    def test_source_support_metadata_covers_every_citation(self):
        for slug in ENTRIES:
            with self.subTest(entry=slug):
                source_doc = self.load(slug, "sources.yaml")
                content = self.load(slug, "content.yaml")
                supported = {
                    source["key"]: set(source["supports"])
                    for source in source_doc["sources"]
                }
                for card, claims in content["cards"].items():
                    for claim in claims:
                        self.assertTrue(
                            any(card in supported[key] for key in claim["sources"]),
                            f"{slug}/{card} lacks matching source support metadata",
                        )


if __name__ == "__main__":
    unittest.main()
