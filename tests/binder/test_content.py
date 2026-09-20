from __future__ import annotations

import copy
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
PROPAGATION_FIELDS = {
    "method", "starting_material", "establishment_condition", "pitfall",
}


class ContentWorksheetTests(unittest.TestCase):
    def load(self, slug: str, filename: str) -> dict:
        # JSON is a deliberately restricted YAML subset, so stdlib validation
        # does not add a repository dependency.
        path = ROOT / "binder" / "entries" / slug / filename
        return json.loads(path.read_text(encoding="utf-8"))

    def assertPropagationContract(self, slug: str, content: dict) -> None:
        claims = content["cards"]["propagation"]
        self.assertTrue(claims, f"{slug}/propagation must not be empty")
        for index, claim in enumerate(claims):
            for field in PROPAGATION_FIELDS:
                self.assertIsInstance(
                    claim.get(field), str,
                    f"{slug}/propagation[{index}] must define {field}",
                )
                self.assertTrue(
                    claim[field].strip(),
                    f"{slug}/propagation[{index}] must not have empty {field}",
                )

    def assertAquaticGuidance(self, content: dict) -> None:
        self.assertIn("Watering interval is N/A", content["environmental_variability"])
        water_claims = content["cards"]["water_parameters_temperature"]
        self.assertTrue(
            any("Watering interval is N/A" in claim["claim"] for claim in water_claims),
            "aquarium-hornwort water card must preserve the N/A watering contract",
        )
        self.assertNotIn("soil_substrate", content["cards"])
        self.assertNotIn("water", content["cards"])
        guidance = [content["environmental_variability"]]
        for claims in content["cards"].values():
            for claim in claims:
                guidance.extend(
                    value for key, value in claim.items()
                    if key != "sources" and isinstance(value, str)
                )
        aquatic_text = " ".join(guidance).casefold()
        for prohibited in ("water thoroughly", "potting soil"):
            self.assertNotIn(prohibited, aquatic_text)

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
                self.assertPropagationContract(slug, content)
                self.assertTrue(content["identity"]["status"])
                self.assertTrue(content["identity"]["decision"])
                self.assertTrue(content["identity"]["sources"])
                self.assertTrue(content["unresolved_fields"])
                self.assertTrue(content["environmental_variability"])
                if slug == "aquarium-hornwort":
                    self.assertAquaticGuidance(content)

                cited = set(content["identity"]["sources"])
                for claims in content["cards"].values():
                    self.assertTrue(claims)
                    for claim in claims:
                        self.assertTrue(claim["claim"])
                        self.assertTrue(claim["sources"])
                        cited.update(claim["sources"])
                self.assertLessEqual(cited, keys)
                unexplained = {
                    source["key"]
                    for source in sources
                    if source["key"] not in cited
                    and source.get("background_only") is not True
                }
                self.assertFalse(
                    unexplained,
                    f"{slug} has uncited sources not marked background_only: "
                    f"{sorted(unexplained)}",
                )

    def test_corrected_kalanchoe_hardiness_and_pothos_care_meanings(self):
        kalanchoe = self.load("kalanchoe-desert", "content.yaml")
        temperature = kalanchoe["cards"]["temperature_season"][0]["claim"]
        self.assertIn("absolute-minimum winter band", temperature)
        self.assertIn("not a summer growing range", temperature)
        self.assertIn("sunny and sheltered", temperature)

        pothos = self.load("pothos", "content.yaml")
        propagation = pothos["cards"]["propagation"][0]
        combined = " ".join(propagation[field] for field in
                            ("claim", *sorted(PROPAGATION_FIELDS))).casefold()
        for phrase in ("node", "bud", "not a detached leaf alone",
                       "foliage above water"):
            self.assertIn(phrase, combined)
        water = pothos["cards"]["water"][0]["claim"].casefold()
        for phrase in ("surface is dry", "thoroughly", "excess drain"):
            self.assertIn(phrase, water)
        feeding = pothos["cards"]["feeding_maintenance"][0]["claim"].casefold()
        self.assertIn("when growth slows", feeding)
        self.assertNotIn("winter dormancy", feeding)

    def test_each_profile_prints_an_interpretable_source_legend(self):
        expected_cues = {
            "kalanchoe-desert": (
                "KAL-RHS—RHS, Desert Surprise",
                "KAL-HARD—RHS, Hardiness rating",
                "KAL-IA—ISU, Kalanchoe care",
                "KAL-PROP—ISU, Propagate succulents",
                "KAL-MSU—Montana State, Growing succulents",
                "KAL-NCSU—NC State, Kalanchoe",
            ),
            "pothos": (
                "POT-NCSU—NC State, ",
                "POT-PSU—Penn State, Pothos",
                "POT-WISC—UW–Madison, Pothos",
                "POT-NCSU-PROP—NC State, Propagation",
            ),
            "sedum-loves-fire": (
                "SED-POWO—Kew, ",
                "SED-PAT—USPTO, LOVE’S FIRE patent",
                "SED-MSU—Montana State, Growing succulents",
                "SED-IA—ISU, Propagate succulents",
            ),
            "bird-of-paradise": (
                "BOP-REG—NC State, ",
                "BOP-NIC—NC State, ",
                "BOP-UF—UF/IFAS, Bird-of-Paradise",
            ),
            "aquarium-hornwort": (
                "HOR-FWS—U.S. FWS, Coon’s-tail",
                "HOR-WA—Washington Ecology, Hornwort",
                "HOR-TROP—Tropica, ",
            ),
        }
        for slug, cues in expected_cues.items():
            with self.subTest(entry=slug):
                page = (ROOT / "binder" / "entries" / slug / "page.tex").read_text(
                    encoding="utf-8")
                self.assertIn(r"\textbf{EVIDENCE / SOURCES}", page)
                printable = page.replace(r"}\allowbreak\texttt{", "")
                self.assertIn(f"binder/entries/{slug}/sources.yaml", printable)
                for cue in cues:
                    self.assertIn(cue, page)

    def test_revised_profiles_keep_reviewer_and_unresolved_footer_fields(self):
        expected_flags = {
            "sedum-loves-fire": (
                "identity/cultivar match", "diagnostic photographs", "exposure", "medium",
                "dry-down/rain", "temperatures",
            ),
            "bird-of-paradise": (
                "species", "diagnostic photographs", "exposure", "pot/medium", "climate",
                "outdoor transition",
            ),
            "aquarium-hornwort": (
                "species/trade form", "diagnostic photographs", "tank", "livestock",
                "chemistry", "light", "flow", "placement", "fertilizer/CO2",
            ),
        }
        for slug, flags in expected_flags.items():
            with self.subTest(entry=slug):
                page = (ROOT / "binder" / "entries" / slug / "page.tex").read_text(
                    encoding="utf-8")
                self.assertIn("Reviewer: pending.", page)
                self.assertIn("Flags:", page)
                self.assertIn("unresolved", page)
                self.assertIn(r"\textbf{EVIDENCE / SOURCES}", page)
                self.assertIn(r"\texttt{sources.yaml}", page)
                for flag in flags:
                    self.assertIn(flag, page)

    def test_sedum_propagation_warns_against_early_placement(self):
        propagation = self.load("sedum-loves-fire", "content.yaml")["cards"][
            "propagation"][0]
        expected_warning = (
            "placing the cutting in medium before the cut end has dried and "
            "callused raises rot risk"
        )
        self.assertIn(expected_warning, propagation["claim"])
        self.assertIn(expected_warning, propagation["pitfall"])
        self.assertIn("dry and callus", propagation["establishment_condition"])
        self.assertNotIn("rooting before callusing", propagation["claim"])

    def test_propagation_contract_rejects_an_empty_required_field(self):
        content = self.load("pothos", "content.yaml")
        content["cards"]["propagation"][0]["pitfall"] = ""
        with self.assertRaisesRegex(AssertionError, "must not have empty pitfall"):
            self.assertPropagationContract("pothos", content)

    def test_hornwort_rejects_terrestrial_advice_in_every_guidance_field(self):
        original = self.load("aquarium-hornwort", "content.yaml")
        fields = (*sorted(PROPAGATION_FIELDS), "environmental_variability")
        for field in fields:
            with self.subTest(field=field):
                content = copy.deepcopy(original)
                if field == "environmental_variability":
                    content[field] += " Use potting soil."
                else:
                    content["cards"]["propagation"][0][field] += " Water thoroughly."
                with self.assertRaises(AssertionError):
                    self.assertAquaticGuidance(content)

    def test_source_support_metadata_covers_every_citation(self):
        for slug in ENTRIES:
            with self.subTest(entry=slug):
                source_doc = self.load(slug, "sources.yaml")
                content = self.load(slug, "content.yaml")
                supported = {
                    source["key"]: set(source["supports"])
                    for source in source_doc["sources"]
                }
                for key in content["identity"]["sources"]:
                    self.assertIn(key, supported, f"{slug}/identity cites unknown source {key}")
                    self.assertIn(
                        "identity", supported.get(key, set()),
                        f"{slug}/identity lacks support metadata for {key}",
                    )
                for card, claims in content["cards"].items():
                    for claim in claims:
                        for key in claim["sources"]:
                            self.assertIn(
                                key,
                                supported,
                                f"{slug}/{card} cites unknown source {key}",
                            )
                            self.assertIn(
                                card,
                                supported.get(key, set()),
                                f"{slug}/{card} lacks support metadata for {key}",
                            )


if __name__ == "__main__":
    unittest.main()
