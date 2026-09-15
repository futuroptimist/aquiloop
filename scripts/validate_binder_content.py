#!/usr/bin/env python3
"""Validate the Step 05 source and claim worksheets (JSON-compatible YAML)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRIES = ROOT / "binder" / "entries"
EXPECTED_CARDS = {
    "sedum-loves-fire": {
        "light_exposure", "soil_substrate", "water", "temperature_season",
        "feeding_maintenance", "propagation", "troubleshooting", "natural_history",
    },
    "kalanchoe-desert": {
        "light_exposure", "soil_substrate", "water", "temperature_season",
        "feeding_maintenance", "propagation", "troubleshooting", "natural_history",
    },
    "pothos": {
        "light_exposure", "soil_substrate", "water", "temperature_season",
        "feeding_maintenance", "propagation", "troubleshooting", "natural_history",
    },
    "bird-of-paradise": {
        "light_exposure", "soil_substrate", "water", "temperature_season",
        "feeding_maintenance", "propagation", "troubleshooting", "natural_history",
    },
    "aquarium-hornwort": {
        "light", "water_parameters_temperature", "placement", "nutrient_context",
        "growth_trimming", "propagation", "compatibility_troubleshooting", "natural_history",
    },
}


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.relative_to(ROOT)} is not valid JSON-compatible YAML: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def validate_entry(slug: str) -> None:
    base = ENTRIES / slug
    sources_doc = load(base / "sources.yaml")
    content = load(base / "content.yaml")
    if sources_doc.get("schema_version") != 1 or content.get("schema_version") != 1:
        raise ValueError(f"{slug}: unsupported schema version")

    source_records = sources_doc.get("sources")
    if not isinstance(source_records, list) or not source_records:
        raise ValueError(f"{slug}: sources must be a nonempty array")
    source_keys = set()
    source_cards = {}
    for source in source_records:
        required = ("key", "authority", "title", "url", "access_date", "supports")
        if not isinstance(source, dict) or any(not source.get(key) for key in required):
            raise ValueError(f"{slug}: each source requires {', '.join(required)}")
        key = source["key"]
        if key in source_keys:
            raise ValueError(f"{slug}: duplicate source key {key}")
        source_keys.add(key)
        supports = source["supports"]
        if not isinstance(supports, dict) or not supports.get("cards") or not supports.get("claims"):
            raise ValueError(f"{slug}/{key}: supports requires nonempty cards and claims")
        source_cards[key] = set(supports["cards"])

    identity = content.get("identity")
    if not isinstance(identity, dict) or not all(identity.get(key) for key in ("status", "preferred_name", "confidence", "notes")):
        raise ValueError(f"{slug}: identity status, preferred name, confidence, and notes are required")
    if not content.get("unresolved_fields"):
        raise ValueError(f"{slug}: unresolved fields must be explicit")

    cards = content.get("cards")
    if not isinstance(cards, dict) or set(cards) != EXPECTED_CARDS[slug]:
        raise ValueError(f"{slug}: card keys must be exactly {sorted(EXPECTED_CARDS[slug])}")
    for card, claims in cards.items():
        if not isinstance(claims, list) or not claims:
            raise ValueError(f"{slug}/{card}: at least one claim is required")
        for claim in claims:
            if not isinstance(claim, dict) or not claim.get("text") or not claim.get("sources"):
                raise ValueError(f"{slug}/{card}: every claim requires text and sources")
            missing = set(claim["sources"]) - source_keys
            if missing:
                raise ValueError(f"{slug}/{card}: unknown source keys {sorted(missing)}")
            unsupported = {key for key in claim["sources"] if card not in source_cards[key]}
            if unsupported:
                raise ValueError(f"{slug}/{card}: source keys do not declare card support {sorted(unsupported)}")
    propagation = " ".join(item["text"].lower() for item in cards["propagation"])
    for required_word in ("method:", "starting material:", "establish", "pitfall:"):
        if required_word not in propagation:
            raise ValueError(f"{slug}/propagation: missing {required_word}")


def validate_all() -> None:
    for slug in EXPECTED_CARDS:
        validate_entry(slug)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entries", nargs="*", choices=sorted(EXPECTED_CARDS))
    args = parser.parse_args()
    for slug in args.entries or EXPECTED_CARDS:
        validate_entry(slug)
        print(f"validated {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
