# Photographed succulents: Powder Puff and Crassula rupestris

The opt-in v7 draft adds the two owner-photographed plants to the v6 reusable
log edition. It reuses PR #112's merged log implementation. PR #113 merged while
this work was in progress. Its safety gates remain unchanged; the candidate
filename, page count and proof inputs advance to v7 so its existing latest-
manifest regression remains valid. This change does not activate publication.
Versions 1-6 remain available.

## Binder index

| Pages | Entry | Page order |
| --- | --- | --- |
| 1-30 | Existing ten entries | Unchanged species sections |
| 31-33 | Pachyveria 'Powder Puff' | Overview, Numbers & Pacifica, Propagation |
| 34-36 | Crassula rupestris | Overview, Numbers & Pacifica, Propagation |
| 37-40 | All twelve tracked entries | Four three-column care logs |
| 41 | Reusable blank log | Unselected preferences; blank names |

The white background, thin category rules, 3.30-inch square hero, punch clearance
and readable type remain. A draft PDF is not a claim of physical print acceptance
or final taxonomic identification.

The standalone `--supplemental watering-log-tracked` command also uses all twelve
entries. Building the historical v6 manifest still uses its original ten-entry
coverage; the blank standalone sheet remains unchanged.

## Photo and identity evidence

Daniel supplied local Downloads copies and authorized repository/binder use,
square cropping, metadata removal and JPEG compression without altering originals.
Actual pixels were inspected on 2026-10-09:

- `IMG_7622.jpg`: label reads `Pachyveria 'Powder Puff' ('Exotica')`.
  'Exotica' remains transcribed label wording, not an independently verified synonym.
- `IMG_7621.jpg`: label reads `Crassula rupestris`; no subspecies is assigned.

Nursery labels support working names, not independent specimen identification.
The photos show indoor pots; they do not establish permanent location, light,
medium, roots, watering history or disease. No Library identity was assigned to
these local copies: the earlier Library transfers failed and their originals
remain untouched in Library.

| Copy | Original size | Square crop | JPEG bytes | Effective resolution |
| --- | --- | --- | --- | --- |
| Powder Puff | 954 x 1271 px | (0, 0, 954, 954) | 99,174 | 289 ppi at 3.30 in |
| Crassula | 954 x 1271 px | (0, 0, 954, 954) | 99,794 | 289 ppi at 3.30 in |

Both crops retain the foreground plant foliage and remove lower pot/saucer area.
No stretching, padding, upscaling or generative editing. Pillow 12.3.0 converted
the embedded Display P3 profile to sRGB pixels before saving fresh RGB JPEGs.
The stripped exports intentionally contain no embedded ICC profile. JPEG marker
inspection found only standard JFIF APP0, with no EXIF/GPS, XMP, IPTC/Photoshop,
MPF or comments. Original hashes were verified unchanged. Exact hashes, crop,
quality and source filenames are recorded in each asset catalog. Every new
repository image is strictly below 100,000 bytes; the builder and regression
tests enforce that decimal ceiling, square geometry and metadata removal.

## Evidence boundaries

[RHS Powder Puff](https://www.rhs.org.uk/plants/522442/-pachyveria-powder-puff/details)
and [RHS Crassula](https://www.rhs.org.uk/plants/4748/crassula-rupestris/details)
provide the named-plant records. RHS H2 is a UK minimum-temperature category,
not a growing optimum. Time to ultimate size is not lifespan or flowering age.
Seed/rooting intervals without sufficiently scoped evidence remain unknown.

[Iowa State propagation](https://yardandgarden.extension.iastate.edu/how-to/how-propagate-succulents),
[Montana State succulent care](https://extension-store.montana.edu/montguides/growing-succulents)
and the [RHS growing guide](https://www.rhs.org.uk/plants/types/cacti-succulents/houseplants/growing-guide)
support explicitly general techniques. The 70/30 established-medium recipe and
home propagation sequence are labeled adaptations, not cultivar-tested results.
Pacifica uses the existing USDA 2023 ZIP 94044 majority 10a record and UC ANR
coastal context; neither measures this home. Cool/foggy conditions prompt
dry-down observation, not a fixed watering calendar. Full scopes and claims live
beside each entry in its YAML records.

## Build and review

```sh
python -m unittest discover -s tests/binder -v
python scripts/build_binder.py --manifest binder/manifest-v7.yaml --mode draft --output build/binder/aquiloop-binder-succulents-draft.pdf
```

CI retains the combined PDF and 150-DPI color/grayscale proofs of pages 31-41.
Check all six new pages, photographs at intended print size, log coverage, source
legibility, safe margins and blank-last order. Exact-head CI, artifact hashes and
digital review results belong in the PR. Physical print/color acceptance remains
pending. No merge, deployment, software installation or publication activation.
