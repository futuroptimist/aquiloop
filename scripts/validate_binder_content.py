#!/usr/bin/env python3
"""Validate JSON-compatible YAML research worksheets for binder entries."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = ROOT / "binder" / "entries"
TERRESTRIAL_CARDS = {"light_exposure", "soil_substrate", "water", "temperature_season", "feeding_maintenance", "propagation", "troubleshooting", "natural_history_trivia"}
AQUATIC_CARDS = {"light", "water_parameters_temperature", "placement", "nutrient_context", "growth_trimming", "propagation", "compatibility_troubleshooting", "natural_history_trivia"}
SOURCE_FIELDS = {"key", "authority", "title", "url", "access_date", "supports"}
REQUIRED_ENTRIES = {"sedum-loves-fire", "kalanchoe-desert", "pothos", "bird-of-paradise", "aquarium-hornwort"}


def _load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: invalid JSON-compatible YAML: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top level must be an object")
    return value


def validate_entry(directory: Path) -> list[str]:
    errors: list[str] = []
    source_path, content_path = directory / "sources.yaml", directory / "content.yaml"
    if not source_path.is_file() or not content_path.is_file():
        return [f"{directory}: sources.yaml and content.yaml are both required"]
    try:
        source_doc, content = _load(source_path), _load(content_path)
    except ValueError as exc:
        return [str(exc)]
    sources = source_doc.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{source_path}: sources must be a nonempty array")
        sources = []
    source_keys: set[str] = set()
    for index, source in enumerate(sources):
        missing = SOURCE_FIELDS - set(source) if isinstance(source, dict) else SOURCE_FIELDS
        if missing:
            errors.append(f"{source_path}: source {index} missing {sorted(missing)}")
            continue
        key = source["key"]
        if key in source_keys:
            errors.append(f"{source_path}: duplicate source key {key}")
        source_keys.add(key)
        if not all(isinstance(source[field], str) and source[field].strip() for field in SOURCE_FIELDS):
            errors.append(f"{source_path}: source {key} metadata must be nonempty strings")
    identity = content.get("identity", {})
    for field in ("status", "confidence", "reported_label", "working_name"):
        if not isinstance(identity.get(field), str) or not identity[field].strip():
            errors.append(f"{content_path}: identity.{field} must be explicit")
    if not isinstance(content.get("unresolved_fields"), list) or not content["unresolved_fields"]:
        errors.append(f"{content_path}: unresolved_fields must be a nonempty array")
    cards = content.get("cards", {})
    expected = AQUATIC_CARDS if content.get("profile_type") == "aquatic" else TERRESTRIAL_CARDS
    if set(cards) != expected:
        errors.append(f"{content_path}: card keys must be exactly {sorted(expected)}")
    for card, claims in cards.items():
        if not isinstance(claims, list) or not claims:
            errors.append(f"{content_path}: {card} must contain claims")
            continue
        for index, claim in enumerate(claims):
            refs = claim.get("sources") if isinstance(claim, dict) else None
            if not isinstance(claim, dict) or not isinstance(claim.get("text"), str) or not claim["text"].strip():
                errors.append(f"{content_path}: {card} claim {index} needs text")
            if not isinstance(refs, list) or not refs:
                errors.append(f"{content_path}: {card} claim {index} needs at least one source")
            elif unknown := set(refs) - source_keys:
                errors.append(f"{content_path}: {card} claim {index} has unknown sources {sorted(unknown)}")
    propagation = content.get("propagation", {})
    for field in ("method", "starting_material", "establishment_condition", "pitfall"):
        if not isinstance(propagation.get(field), str) or not propagation[field].strip():
            errors.append(f"{content_path}: propagation.{field} must be explicit")
    if content.get("profile_type") == "aquatic" and content.get("watering_interval") != "N/A":
        errors.append(f"{content_path}: aquatic watering_interval must be N/A")
    return errors


def validate_all(entries: Path = ENTRIES) -> list[str]:
    research = [path.parent for path in entries.glob("*/content.yaml")]
    present = {path.name for path in research}
    errors = [f"{entries}: missing required worksheets {sorted(REQUIRED_ENTRIES - present)}"] if REQUIRED_ENTRIES - present else []
    return errors + [error for directory in sorted(research) for error in validate_entry(directory)]


if __name__ == "__main__":
    problems = validate_all()
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)
    print("Validated all binder research worksheets.")
