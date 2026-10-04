# Kuhli loach care and binder extension

K227, 2026-10-04. Add an animal care section without renaming the binder or
changing the approved plant pages. Daniel reports two Kuhli loaches resident
about three years in a filtered 20-gallon tank with an air stone, hornwort and
guppy grass. Exact Pangio species, age, footprint, total stock and water results
remain unverified. No purchase, stocking change or physical tank action follows
from this design.

## Research decisions

Use **Pangio spp.**, not a claimed identification of P. kuhlii. The source inventory
and 26 scoped claims live in [the entry](../../binder/entries/kuhli-loach/sources.yaml).
Every source was inspected on 2026-10-04; the university source is explicitly an
abstract, not a full-paper review. The companion PDFs link to their bibliography
URLs, while worksheets preserve evidence categories and applicability.

- Social recommendations differ: Aquarium Co-Op suggests 3–6 or more; Seriously
  Fish gives 5–6 minimum for P. semicincta. These support reviewing the pair's
  welfare, not adding a calculated number of fish. Review footprint, stock,
  health, shelter, water and quarantine first.
- Temperature and chemistry are species-scoped. The broad P. semicincta ranges
  include very acidic, low-mineral conditions; they are not proposed home targets.
  The warmer historical Loaches Online guidance remains separate. Do not average
  conflicting endpoints or abruptly alter established fish water. Numeric KH and
  individual lifespan remain justified unknowns.
- Deliberate sinking-food access matters. Shelter, soft substrate, gentle
  circulation, covered intakes and a lid form the habitat checklist. Java moss,
  Java fern, Cryptocoryne and optional Anubias nana are proposed plant choices;
  existing hornwort/guppy grass are owner-reported. No new plant entry or glue
  recipe is implemented here.
- Peaceful fish are conditional candidates. Exclude aggressive, nipping,
  predatory or incompatible-temperature companions from the plan. Adult shrimp
  coexistence does not establish juvenile, egg or post-molt safety. Predation risk
  is an explicit inference, not a measured loss rate for these two loaches.
- Breeding guidance is an observation/preparation plan, not an induction recipe.
  The 2024 reproductive study's published species name does not identify this
  pair. Hatch interval and maturity age are unknown. Do not prescribe hormones,
  stripping, forced sexing, deliberate overfeeding or abrupt spawning triggers.

These decisions synthesize the linked sources; precise claims and citations are
in the worksheets rather than duplicated as a second numerical authority.
[Aquarium Co-Op](https://www.aquariumcoop.com/blogs/aquarium/care-guide-for-kuhli-loaches),
[Seriously Fish](https://www.seriouslyfish.com/species/pangio-semicincta/),
[Loaches Online](https://www.loaches.com/species-index/pangio-semicincta),
[veterinary management](https://www.msdvetmanual.com/exotic-and-laboratory-animals/aquarium-fish/management-of-aquarium-fish),
[university study record](https://scholar.unair.ac.id/en/publications/primary-and-secondary-sexual-characteristics-of-kuhli-loach-pangi/).

## Controlled assembly and layout

`binder/manifest.yaml` stays six pages and `binder/manifest-v2.yaml` stays sixteen.
The opt-in `binder/manifest-v3.yaml` preserves those sixteen expanded pages in
place, including the log, and appends this three-page animal section:

| Page | Kind | Purpose |
| --- | --- | --- |
| 17 | `animal-care` | Identity, social welfare, feeding, temperature and observations |
| 18 | `tank-setup` | Scoped water evidence, habitat, plants, quarantine and measurements |
| 19 | `reproduction` | Evidence limits, observation sequence, tankmates and shrimp risk |

Each page independently has a one-page Letter budget. Reuse the companion
typography, white paper, unfilled cards, one-inch punch clearance and existing
safe rectangle. Body remains 9.5 pt and sources 8 pt. No specimen photograph is
available or invented; no new asset catalog is needed. Animal pages add clickable
source links through a build-local hyperref addition, leaving the shared template
and existing rendered pages unchanged. Their right margin is inset to 0.56 inches
so writing rules stay strictly inside the safe rectangle even after PDF coordinate
arithmetic. No bounds tolerance is relaxed. Category color accents are separate work.

Animal worksheets use `care_method` and life stages `adult`, `egg`, `juvenile`,
or `all`; they never need a plant propagation field, soil recipe, USDA zone or
germination card. Reuse the existing numeric/provenance validator with an explicit
animal mode. Published/proposed statements cite known HTTPS sources; proposals
include derivations; unknown values state why. IDs are unique across all three
worksheets. Layout claim references and source URLs must resolve. Animal images
remain unsupported pending a reviewed rights/catalog workflow. Final mode remains
unavailable until identity and publication review; digital proof is draft only.

## Reproduction and verification

```sh
python -m unittest discover -s tests/binder -v
python scripts/build_binder.py --entry kuhli-loach --kind animal-care --mode draft --output build/binder/kuhli-care.pdf
python scripts/build_binder.py --manifest binder/manifest-v3.yaml --mode draft --output build/binder/aquiloop-binder-kuhli-draft.pdf
```

The pinned CI environment builds all three assemblies and uploads the new
`aquiloop-binder-kuhli-proof` artifact: nineteen-page PDF plus 150-DPI color and
grayscale PNGs. Existing artifacts remain available. Tests cover canonical order,
entry-level overflow, geometry, safe text/paint bounds, bibliography links and
pixel-identical first sixteen pages in both modes. Inspect all new pages at 100%
and compare the inherited pages with the accepted proof before human review.
Physical printing, punching and handwriting acceptance are still separate gates.

Starting main is `789e392657c89354df2b7a3d53657d8dedd7b14a` (merged #108):
normal main Link Check and Lint passed. #108 changed only its shrimp document, so
no fresh binder run was expected. Binder inputs match main #107 at `11cb6b1`;
the existing main artifact from run `37186677750` was reverified: 16 pages,
32 unchanged color/grayscale PNGs, PDF SHA-256
`410e9d3e2f2fd4b21fc083da66bd1eda712d6b8307b7f40b90bac6ba3ad2663e`.

## Separate follow-ups

Cherry shrimp are selected for a later authorized binder PR; a possible
10-gallon nursery and adult transfers to the 20-gallon remain planning questions.
That tank is not automatically also a fish quarantine or Kuhli nursery. Guppy
grass, Java moss, Anubias nana and subtle category accents remain separate work.
The binder name and existing content remain unchanged. K161 physical proof is
pending; a successful PDF build cannot complete it.
