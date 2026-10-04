"""Validate companion research without altering the overview contract."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import re

ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def read(path: Path) -> dict:
    def reject(value):
        raise ValueError(f"non-finite JSON number: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal,
                      parse_constant=reject)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def number(value):
    return type(value) in (int, Decimal) and Decimal(value).is_finite()


def claim_references(value):
    """Find references in page panels as well as the top-level shared list."""
    if isinstance(value, dict):
        if "claim_ref" in value:
            require(text(value["claim_ref"]), "claim reference must be nonempty text")
            yield value["claim_ref"]
        for child in value.values():
            yield from claim_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from claim_references(child)


def validate_claim(c: dict, sources: dict, *, animal: bool = False) -> None:
    require(isinstance(c, dict), "claim must be an object")
    if animal:
        allowed = {"claim_id", "metric", "applicable_taxon", "care_method", "life_stage",
                   "growing_conditions", "geographic_context", "evidence_category",
                   "provenance", "quantity", "description"}
        require(set(c) <= allowed, "unsupported animal claim field")
    for field in ("claim_id", "metric", "applicable_taxon", "care_method" if animal else "propagation_method",
                  "life_stage", "growing_conditions", "geographic_context", "evidence_category"):
        require(text(c.get(field)), f"claim requires {field}")
    require(ID.fullmatch(c["claim_id"]), "invalid claim ID")
    stages = {"adult", "egg", "juvenile", "all"} if animal else {"established", "seed", "cutting", "division", "fragment"}
    require(c["life_stage"] in stages, "invalid life stage")
    require(sum(k in c for k in ("quantity", "description", "recipe")) == 1, "exactly one payload required")
    evidence, provenance = c["evidence_category"], c.get("provenance")
    require(isinstance(provenance, dict), "provenance must be an object")
    require(evidence in {"published", "proposed", "observed", "unknown", "not_applicable"}, "invalid evidence category")
    q = c.get("quantity")
    if q is not None:
        require(isinstance(q, dict), "quantity must be an object")
        kind = q.get("kind")
        if kind in {"unknown", "not_applicable"}:
            require(set(q) == {"kind", "reason"} and text(q["reason"]), "state envelope requires only kind and reason")
            require(evidence == kind and not provenance.get("source_refs"), "state evidence mismatch or fabricated citation")
        elif kind == "value":
            require(set(q) == {"kind", "value", "unit"} and number(q["value"]) and text(q["unit"]), "invalid numeric value")
        elif kind == "range":
            require(set(q) == {"kind", "minimum", "maximum", "unit"}, "invalid range fields")
            require(number(q["minimum"]) and number(q["maximum"]) and q["minimum"] <= q["maximum"] and text(q["unit"]), "invalid ordered range")
        else:
            raise ValueError("invalid quantity kind")
    if evidence in {"unknown", "not_applicable"}:
        require(q is not None and q.get("kind") == evidence, "state requires matching quantity")
    else:
        require(q is None or q.get("kind") in {"value", "range"}, "known evidence requires known payload")
    if "description" in c:
        require(text(c["description"]), "empty description")
    if evidence in {"published", "proposed"}:
        refs = provenance.get("source_refs")
        require(isinstance(refs, list) and refs and all(text(k) and k in sources for k in refs), "unresolved citation")
        require(text(provenance.get("applicability")), "missing applicability")
        if evidence == "proposed":
            require(text(provenance.get("derivation")), "missing derivation")
    if evidence == "observed":
        require(all(text(provenance.get(k)) for k in ("date", "method", "conditions")), "missing local provenance")
        require(date.fromisoformat(provenance["date"]).isoformat() == provenance["date"], "invalid observation date")
    if "recipe" in c:
        r = c["recipe"]
        require(isinstance(r, dict) and r.get("recipe_basis") == "percent_by_volume" and r.get("batch_volume_litres") == 10, "invalid recipe basis")
        require(r.get("recipe_evidence") in {"directly_published", "adapted", "proposed_starting_point"}, "invalid recipe label")
        require((r["recipe_evidence"] == "directly_published" and evidence == "published") or
                (r["recipe_evidence"] in {"adapted", "proposed_starting_point"} and evidence == "proposed"), "recipe evidence mismatch")
        components = r.get("components")
        require(isinstance(components, list) and components, "empty recipe")
        for part in components:
            require(text(part.get("name")) and text(part.get("purpose")), "ingredient name and purpose required")
            batch_keys = {"litres_per_10_litre_batch", "litres_for_10_litre_batch"} & part.keys()
            require(len(batch_keys) == 1, "exactly one batch conversion required")
            percent, litres = part.get("percent_by_volume"), part[next(iter(batch_keys))]
            require(number(percent) and 0 <= percent <= 100 and number(litres), "invalid recipe quantity")
            require(Decimal(percent) / 10 == Decimal(litres), "incorrect 10-litre conversion")
        require(sum(Decimal(p["percent_by_volume"]) for p in components) == 100, "recipe must total exactly 100 percent")


def load_companions(root: Path, entry: str) -> dict:
    base = root / "binder" / "entries" / entry
    sources = {}
    for path in (base / "sources.yaml", root / "binder/contexts/sources.yaml"):
        doc = read(path)
        require(doc.get("schema_version") == 1, "unsupported bibliography schema")
        for source in doc["sources"]:
            key = source["key"]
            require(key not in sources, "duplicate source key")
            require(all(text(source.get(k)) for k in ("key", "authority", "title", "accessed", "url")) and source["url"].startswith("https://"), "invalid bibliography record")
            sources[key] = source
    documents, claims = {}, {}
    for kind in ("numbers", "propagation"):
        d = read(base / f"{kind}.yaml")
        require(d.get("schema_version") == 1 and d.get("entry") == entry and d.get("worksheet") == kind, "worksheet identity mismatch")
        require(isinstance(d.get("claims"), list) and d["claims"], "claims array required")
        for c in d["claims"]:
            validate_claim(c, sources)
            ref = entry + "#" + c["claim_id"]
            require(ref not in claims, "duplicate entry claim ID")
            claims[ref] = c
        documents[kind] = d
    context = read(root / "binder/contexts/pacifica.yaml")
    context_ref = context["context_id"] + "#" + context["hardiness"]["lookup"]["claim_id"]
    valid_refs = set(claims) | {context_ref}
    for d in documents.values():
        for ref in claim_references(d):
            require(ref in valid_refs, "unresolved claim reference")
    # Preserve overview checks: companion use supplements, never replaces, them.
    overview = read(base / "content.yaml")
    used = set(overview["identity"]["sources"])
    for card in overview["cards"].values():
        for c in card:
            used.update(c["sources"])
    for c in claims.values():
        used.update(c["provenance"].get("source_refs", []))
    for source in read(base / "sources.yaml")["sources"]:
        require(source["key"] in used or source.get("background_only") is True, "unused non-background entry source")
    return {"documents": documents, "claims": claims, "sources": sources, "valid_refs": valid_refs}


ANIMAL_PAGE_KINDS = ("animal-care", "tank-setup", "reproduction")


def load_animal(root: Path, entry: str) -> dict:
    """Animal claims reuse evidence rules without plant stages or climate context."""
    require(isinstance(entry, str) and ID.fullmatch(entry), "invalid animal entry ID")
    base = root / "binder/entries" / entry
    bibliography = read(base / "sources.yaml")
    require(bibliography.get("schema_version") == 1 and bibliography.get("entry") == entry,
            "animal bibliography identity mismatch")
    sources = {}
    for source in bibliography.get("sources", []):
        require(isinstance(source, dict), "source must be an object")
        require(all(text(source.get(k)) for k in ("key", "authority", "title", "accessed", "url", "applicability")),
                "invalid animal bibliography record")
        require(source["url"].startswith("https://"), "source requires HTTPS")
        require(source["key"] not in sources, "duplicate source key")
        date.fromisoformat(source["accessed"])
        sources[source["key"]] = source
    require(sources, "animal bibliography required")
    documents, claims, used = {}, {}, set()
    for kind in ANIMAL_PAGE_KINDS:
        document = read(base / f"{kind}.yaml")
        require(document.get("schema_version") == 1 and document.get("entry") == entry
                and document.get("worksheet") == kind, "animal worksheet identity mismatch")
        require(isinstance(document.get("claims"), list) and document["claims"], "claims array required")
        for claim in document["claims"]:
            validate_claim(claim, sources, animal=True)
            ref = entry + "#" + claim["claim_id"]
            require(ref not in claims, "duplicate animal claim ID")
            claims[ref] = claim
            used.update(claim["provenance"].get("source_refs", []))
        documents[kind] = document
    for document in documents.values():
        for ref in claim_references(document):
            require(ref in claims, "unresolved animal claim reference")
    for key, source in sources.items():
        require(key in used or source.get("background_only") is True, "unused non-background animal source")
    return {"documents": documents, "claims": claims, "sources": sources, "valid_refs": set(claims)}
