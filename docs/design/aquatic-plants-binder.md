# Aquatic plant extension and category accents

Guppy grass is owner-reported; Java moss and Anubias nana are requested planning
entries, not records of acquisition. Their working names are Najas guadalupensis,
Taxiphyllum barbieri and Anubias barteri var. nana. Exact specimens remain
unverified. All three overview frames are honest text-only placeholders until
Daniel supplies and authorizes photographs. No stock or generated images.

The opt-in manifest-v5.yaml builds 31 pages: the prior 21 species pages, three
pages each for guppy grass, Java moss and Anubias nana, then the unchanged watering
log on page 31. Each plant has overview, numbers/context and sequential
propagation pages. No binder rename. Versions 1-4 retain their appearance and
content; the new assembly applies category styling without modifying prior
entry sources or templates on disk.

Thin rules use muted green (#557064) for terrestrial plants and blue (#486B83)
for aquatic plants and animals. Written category labels distinguish aquatic
plants from animals, including in grayscale. Body text remains dark, backgrounds
white, punch clearance and page budgets unchanged. These are small accents,
not filled panels. Digital and physical color acceptance remain separate.

## Research decisions

All cited URLs were inspected on 2026-10-04. Adjacent sources.yaml records scope;
canonical claims preserve provenance, explicit unknowns and proposed derivations.
Extension sources establish guppy-grass morphology, flowering and fragment
regrowth; their pond herbicides, carp stocking and bulk transplant practices
are not aquarium instructions. Aquatic Arts provides a separately scoped
commercial 64-86 F (18-30 C as published), pH 5.5-7.5 profile. This neither measures
the tank nor sets livestock-compatible targets. Calflora's annual life cycle
is not a lifespan for a repeatedly divided aquarium clone.

Tropica's Taxiphyllum barbieri stock supports low light, surface attachment and
pruning. Numeric water targets remain unknown rather than borrowed from another
moss. Moss seed germination/flowering are not applicable; spore culture is outside
this fragment plan. Co-Op's no-light and indestructibility claims are not adopted.
Tropica mat thickness and its open-ended two-month height category stay distinct.

Dennerle's Anubias nana stock profile supplies 22-28 C, pH 5-9 and rhizome
cuttings. Fahrenheit is a rounded conversion. Keep rhizomes exposed; roots may
enter substrate. Tropica's 5-10 cm narrative and 5-15+ cm two-month table are
reported separately. Leaf longevity and underwater flowers do not establish
whole-plant lifespan or a flowering deadline.

Glue is optional for moss/Anubias, unnecessary for the primary floating guppy
grass method. Instructions name Seachem Flourish Glue, an aquarium-labeled
cyanoacrylate gel: small root/moss contact points and a 20-second hold. This is
not universal glue compatibility, full cure time, or biological establishment.
Keep tips and rhizomes uncoated; do not attach to glass; follow the actual product
label and its skin/eye bonding warning. Mechanical ties remain an alternative.
No purchase or physical attachment is authorized by these reference pages.

No blanket fertilizer, CO2, nitrate, lamp runtime, seed germination, cutting size,
leaf count, establishment timetable or predation-safe shelter is invented.
Actual water, light, stock and additive regimen remain unresolved. Pacifica
outdoor climate does not set tank parameters. NY DEC supports containment and
sealed-trash disposal, not outdoor release or composting.

## Validation and deliverable

Run `python -m unittest discover -s tests/binder -v`, then build with
`python scripts/build_binder.py --manifest binder/manifest-v5.yaml --mode draft --output build/binder/aquiloop-binder-aquatic-draft.pdf`.
CI uploads the PDF plus 150-DPI color/grayscale proofs. Check all new pages,
category labels, geometry, links, white margins, source scope and final log.
Final head checks and artifact hashes belong in the PR. Physical print/punch/
handwriting and photo/color acceptance remain pending; no merge or live actions.
