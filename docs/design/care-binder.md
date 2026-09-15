# Home, garden, and aquarium care binder design brief

Status: approved design direction; the single-entry draft template and local
photo workflow are implemented. Final care copy, five-entry assembly, care log,
and release automation remain future work.

## Purpose and sequence

The first release is one directly printable, six-page PDF in this exact order:

1. Sedum “Love’s Fire” profile (reported Lowe’s label; outdoor grow bag).
2. *Kalanchoe humilis* “Desert Surprise” profile (reported Lowe’s label;
   outdoor grow bag).
3. Pothos profile (indoors).
4. Bird of paradise profile (indoors initially).
5. Aquarium hornwort profile.
6. Handwritten watering log.

Each profile occupies exactly one page. The concept studies below are retained
as historical exploration, not evidence: generated plants are provisional, and
the final committed photographs must show the user's actual specimens.

The facts currently supplied are intentionally sparse. “Soil plus additives”
does not establish a recipe, and Pacifica, California is prior location context,
not a measured growing-site condition. Draft content and pages may use clearly
provisional identities, general source-backed guidance, unresolved fields, and
the visible placeholder; they do not wait for photographs. Photograph-qualified
final copy depends on reviewed specimen images, rights, and the inputs listed
under [Required specimen inputs](#required-specimen-inputs-for-final-photograph-qualification).

## Visual references

These references were inspected on 2026-09-14 for visual language only. They
are not factual care sources. A link, even to openly accessible media, does not
itself grant redistribution permission; verify the particular asset's rights
statement before reuse. Final production should prefer original specimen photos.

| Reference | Creator/source | Useful feature | Reuse status for this project |
| --- | --- | --- | --- |
| [USWDS card component](https://designsystem.digital.gov/components/card/) | U.S. Web Design System, U.S. General Services Administration | Restrained cards, consistent headings, clear grouping, and responsive grid examples | Design inspiration only. USWDS states its code and documentation are freely reusable, but third-party content can have separate terms; do not copy an unexplored asset. |
| Smithsonian Open Access (`https://www.si.edu/openaccess`) | Smithsonian Institution | Object-first presentation, ample negative space, compact metadata, and high-resolution specimen imagery | A portal, not a blanket decision for every object. Use only an item explicitly marked CC0 and retain its object record/provenance. |
| *Flora von Deutschland, Österreich und der Schweiz* (`https://www.biodiversitylibrary.org/item/10337`) | Otto Wilhelm Thomé; Biodiversity Heritage Library scan | Botanical plate hierarchy: isolated specimen, detail studies, caption, and plate number | BHL identifies item/page rights separately. Treat as inspiration until the exact page's rights field is recorded; never assume the whole portal is reusable. |
| [Nature Journaling](https://www.nps.gov/kefj/learn/education/classrooms/nature-journaling.htm) | Kenai Fjords National Park, U.S. National Park Service | Observation-led page with drawing, labels, date/place context, questions, and handwritten character | Design inspiration only. U.S. government material is often public domain, but verify credits and exceptions for each image/download. |

### Comparable concept directions

These directions record the exploration that preceded approval; their prompts
are not current production requirements and do not imply that generated images
or chat artifacts are repository assets.

All three prompts deliberately use the same specimen and content load so the
review compares composition rather than subject matter. Every concept must
remain legible in grayscale and reserve the same generous punch margin.

#### A. Botanical field guide

Use a quiet archival page, a large scientifically observed macro image, serif
display typography, fine rules, and restrained botanical accents. A numbered
detail inset may explain a genuinely useful feature such as leaf arrangement;
it must not become decoration or imply an unverified diagnostic trait.

**Image-generation prompt:**

> Create a straight-on, print-layout mockup of one US Letter portrait plant-care
> page for Sedum “Love’s Fire.” Use a 1.0-inch blank left punch margin and
> 0.55-inch top, right, and bottom safe margins. Feature one prominent macro
> photograph of a mature potted succulent occupying about 38% of the usable
> page. Show the reported common/cultivar label “Sedum ‘Love’s Fire’” and the
> provisional binomial “Sedum adolphi — identity pending verification.” Arrange
> eight concise, clearly separated information items: identity/origin/habit;
> light/acclimation; soil; watering trigger/method; temperature/season;
> feeding/maintenance; troubleshooting; trivia. Add a compact sources/revision
> footer and one small numbered leaf-arrangement detail diagram. Style it as a
> refined botanical field guide: warm white paper, dark ink, classic serif
> title, readable sans-serif body, hairline rules, muted rust and sage accents,
> high contrast, no tiny text, no invented care values, no logos, no extra
> plants, no perspective view, useful when printed in grayscale.

#### B. Modern modular care cards

Use a strong sans-serif hierarchy and a disciplined modular grid. Cards must
encode categories with words as well as color; icons may reinforce headings but
never replace them. Avoid dashboard density and decorative “app UI” controls.

**Image-generation prompt:**

> Create a straight-on, print-layout mockup of one US Letter portrait plant-care
> page for Sedum “Love’s Fire.” Use a 1.0-inch blank left punch margin and
> 0.55-inch top, right, and bottom safe margins. Feature one prominent macro
> photograph of a mature potted succulent occupying about 38% of the usable
> page. Show the reported common/cultivar label “Sedum ‘Love’s Fire’” and the
> provisional binomial “Sedum adolphi — identity pending verification.” Arrange
> eight concise, clearly separated information items: identity/origin/habit;
> light/acclimation; soil; watering trigger/method; temperature/season;
> feeding/maintenance; troubleshooting; trivia. Add a compact sources/revision
> footer and one small numbered leaf-arrangement detail diagram. Style it as
> modern modular care cards: crisp sans-serif type, two-column grid, generous
> whitespace, squared cards with subtle rules, simple labeled icons, restrained
> terracotta and deep green accents, high contrast, no tiny text, no invented
> care values, no logos, no extra plants, no perspective view, useful when
> printed in grayscale.

#### C. Annotated specimen notebook

Pair an orderly underlying grid with the warmth of field annotations. Handwritten
elements are accents only; all care instructions and evidence labels remain in
highly readable typeset text. Callouts should record observations, not fabricate
measurements or specimen history.

**Image-generation prompt:**

> Create a straight-on, print-layout mockup of one US Letter portrait plant-care
> page for Sedum “Love’s Fire.” Use a 1.0-inch blank left punch margin and
> 0.55-inch top, right, and bottom safe margins. Feature one prominent macro
> photograph of a mature potted succulent occupying about 38% of the usable
> page. Show the reported common/cultivar label “Sedum ‘Love’s Fire’” and the
> provisional binomial “Sedum adolphi — identity pending verification.” Arrange
> eight concise, clearly separated information items: identity/origin/habit;
> light/acclimation; soil; watering trigger/method; temperature/season;
> feeding/maintenance; troubleshooting; trivia. Add a compact sources/revision
> footer and one small numbered leaf-arrangement detail diagram. Style it as an
> annotated specimen notebook: off-white stock, faint measured grid, taped-photo
> illusion, tidy ink callout leaders and sparse handwritten accent labels, while
> all care text is clean typeset sans serif; graphite, muted ochre and olive
> palette, high contrast, no tiny text, no invented care values, no logos, no
> extra plants, no perspective view, useful when printed in grayscale.

## Page and content contract

### Approved visual direction

The approved profile combines **A's typography** with **B's layout**: a large
serif common-name heading, italic botanical name, and restrained botanical
accents; title and identity at upper left; a prominent framed hero photograph
at upper right; and a two-column care-card grid below. The approved **H care
log** uses thin dark rules, a pale header tint, date/time plus five plant
columns, and comfortable handwriting space. These choices supersede the
full-width photograph in the exploratory prompts while preserving their useful
historical record.

### Physical page and typography

- Page box: US Letter portrait, exactly 8.5 × 11 inches (612 × 792 PDF points).
- Safe area: 1.0-inch left margin for three-hole punching; 0.55 inch at top,
  right, and bottom. No essential ink enters those margins. The resulting usable
  rectangle is 6.95 × 9.9 inches.
- Hero photograph: an initial 3.30 × 3.30-inch square frame at upper right,
  cropped without misleading scale. The rendered crop requires at least
  792 × 792 pixels (240 ppi) and preferably 990 × 990 pixels (300 ppi), plus
  appropriate color interpretation, descriptive alt/source metadata, and a
  grayscale contrast check. Later rendered-page qualification may adjust the
  chosen starting frame dimensions.
- Grid: two equal content columns with a 0.22-inch gutter; one category per
  bounded item. Keep headings with their content and prohibit stranded labels.
- Type: 24–30 pt common name; 14–17 pt binomial/status line; 11–12 pt category
  headings; 9.5–10.5 pt body with at least 1.25× line spacing; 8 pt minimum for
  sources/revision metadata. Never shrink type to cure overflow.
- Output: near-black body text on white or near-white, minimum 4.5:1 contrast
  for ordinary text, no information conveyed by hue alone, solid/dashed or
  labeled distinctions that survive grayscale, and 0.5 pt minimum rules.

### Profile content schema

Every assertion should fit one of these labeled items and carry an evidence
status where ambiguity matters: **reported**, **verified**, **general guidance**,
or **local starting point**.

Place identity, family, origin, and growth habit in the header rather than a
care card. The terrestrial grid has these eight distinctly labeled cards:

1. **Light / exposure:** broadly supported needs, actual measured exposure,
   acclimation steps, and sunburn or etiolation cues.
2. **Soil / substrate:** observed current medium and a practical composition by
   volume only when an authoritative or identifiable grower source supports it.
   A proposed local mix must be labeled as a starting point, not universal fact.
3. **Water:** observable trigger first, thoroughness/method and drainage second,
   then a conditional interval range if observations support one. Calendar
   intervals never override moisture, plant condition, rain, or season.
4. **Temperature / season:** supported tolerances, frost/heat response, seasonal
   light, water, and indoor/outdoor transition adjustments.
5. **Feeding / maintenance:** conditional feeding, pruning, repotting, cleaning,
   or aquarium trimming as appropriate.
6. **Propagation:** a supported method, the starting material, and one key
   establishment condition or pitfall. Every profile must show this card;
   detailed propagation guides are future entries with explicit page budgets.
7. **Troubleshooting:** a compact symptom → plausible cause → safe next check
   table; avoid a diagnosis from appearance alone.
8. **Natural history / trivia:** one sourced species/genus fact that cannot be
   mistaken for care.

An **evidence footer** carries short source keys, revision date/version,
reviewer, and unresolved identity or measurement flags.

Every record in an entry's `sources.yaml` must be cited by its identity or card
content. A source retained only for research context must instead declare
`"background_only": true`; this exception should be uncommon and intentional.

Optional diagrams are allowed only when they clarify a task or observation—for
example, a leaf/node detail, pruning point, planting depth, or grow-bag moisture
sampling locations. They need a caption and source/“schematic” label and must not
crowd out the photograph or care grid.

### Species image catalogs and page placements

The planned source layout gives each species a reusable image catalog. This tree
is illustrative; none of these photographs, catalogs, or page sources is claimed
to exist yet:

```text
binder/
  manifest.yaml
  template.tex
  entries/
    sedum-loves-fire/
      page.tex
      sources.yaml
      assets.json
      assets/
        overview.jpg
        roots.jpg
        leaf-discoloration.jpg
```

Other species follow the same pattern. A future source such as
`propagation.tex` may live beside `page.tex` and share that species'
`assets.json` and `assets/`. Factual care citations belong in `sources.yaml`,
not in the image catalog.

Catalog records use stable IDs that describe assets independently of page roles.
Adding a record never selects an image for the PDF. The following small,
versioned example is valid JSON but entirely hypothetical:

```json
{
  "schema_version": 1,
  "assets": [
    {
      "id": "sedum-overview-001",
      "path": "assets/overview.jpg",
      "kind": "photograph",
      "subjects": ["whole plant", "growth habit"],
      "alt": "Hypothetical Sedum specimen shown from the side in its grow bag.",
      "caption": "Whole-plant view of the documented specimen.",
      "source": {
        "photographer": "unknown",
        "provenance": "hypothetical example; not a repository asset",
        "rights": "unknown"
      },
      "specimen_id": "example-specimen-01",
      "capture_date": "2026-09-01",
      "observations": ["Multiple stems are visible above the bag rim."]
    },
    {
      "id": "sedum-leaf-001",
      "path": "assets/leaf-discoloration.jpg",
      "kind": "photograph",
      "subjects": ["leaf", "discoloration"],
      "alt": "Hypothetical close view of one lower leaf with yellow coloration.",
      "caption": "Yellow coloration observed on one lower leaf; cause not established.",
      "source": {
        "photographer": "unknown",
        "provenance": "hypothetical example; not a repository asset",
        "rights": "unknown"
      }
    }
  ]
}
```

Unknown metadata remains absent or explicitly `"unknown"`; it must never be
guessed. Draft and unselected catalog entries may retain unknown rights, subject
to the final-selection rules below. Pixel dimensions, encoded format, and byte
size are measured from the file during preparation and validation rather than
duplicated as manually maintained JSON values. Optional `specimen_id`,
`capture_date`, and factual `observations` associate an image with evidence
without turning an observation into a diagnosis. In particular, a yellow lower
leaf does not establish its cause, and a photograph alone cannot establish
root-zone moisture or a universal watering trigger.

A page selects each image explicitly by asset ID and supplies its placement/slot,
printed dimensions, fit/crop behavior, and an optional contextual caption
override. **Hero** and **detail** are placement roles, not asset properties, so a
page may reuse an asset without copying its binary. A summary supports one hero
and up to two optional details only when all required care text still fits.
Absent details leave no reserved empty boxes and do not block publication.
Useful details may show roots, nodes, leaf discoloration, or a moisture-check
procedure; roots and diagnostic views must not be forced into the hero crop.

Every source-level placement must have an adjacent comment that states the asset
ID and resolvable file reference; printed dimensions, aspect ratio, and
orientation; preferred and minimum pixels for the rendered crop; fit/crop
behavior; and practical capture guidance. Initial frame contracts are:

| Slot | Printed frame | Preferred crop | Minimum crop | Capture guidance |
| --- | --- | --- | --- | --- |
| Hero | 3.30 × 3.30 in, 1:1 square | 990 × 990 px (300 ppi) | 792 × 792 px (240 ppi) | Leave crop room around the whole plant and keep identifying features sharp. |
| Detail 1 or 2 | 2.05 × 1.35 in, about 3:2 landscape | 615 × 405 px (300 ppi) | 492 × 324 px (240 ppi) | Fill the frame with the relevant root, node, leaf, or procedure while retaining context. |

These dimensions are starting points subject to rendered-page qualification;
the comment must describe the placement actually used. Reuse at a larger print
size requires a new effective-resolution check. DPI metadata changes and
upscaling do not replace captured detail.

Catalog capacity is independent of page capacity. Excess images appear only on
explicitly authored future pages with their own budgets. An image must never
cause type to shrink below the minimum, care text to be discarded, or content to
silently spill onto another page.

### Photograph preparation workflow

1. Capture and retain the original outside the repository.
2. Apply orientation, choose an intentional crop, convert to sRGB, and resize
   once while preserving enough real detail for the intended frame.
3. Create a separate compressed JPEG derivative for a photograph. Remove
   unnecessary EXIF and GPS metadata while preserving appropriate color
   interpretation.
4. Aim for approximately 500 KiB or less for each hero and retain the planned
   1 MiB ceiling for any raster, without sacrificing minimum resolution or
   useful detail.
5. Upload the derivative into the species' `assets/` directory, add or update
   its catalog record, and select its ID from a page only when desired.

The implemented helper preserves originals and reports the derivative's measured
dimensions, bytes, and effective print resolution. For example:

```sh
python scripts/prepare_binder_photo.py original.jpg \
  binder/entries/sedum-loves-fire/assets/overview.jpg \
  --frame hero --crop 100,0,1300,1200
```

Retain `original.jpg` outside Git; choose the crop deliberately; create the
derivative; add its metadata to `assets.json`; select its stable ID in the
adjacent `page.tex` placement comment; then rebuild. Existing derivatives need
an explicit `--overwrite`. This is intentionally not a media-management service.

### Aquatic adaptation

Hornwort keeps identity and growth form in the header, then adapts the eight
cards to **light**, **water parameters and temperature**, **placement/anchoring
or floating**, **nutrient context**, **growth/trimming**, **propagation**,
**aquarium compatibility/troubleshooting**, and **natural history/trivia**. Its
Propagation card follows the same method, starting-material, and establishment
condition/pitfall contract. It must not receive terrestrial soil or watering
instructions.
Record tank volume, temperature, light schedule/intensity, livestock, filtration,
fertilization, and measured chemistry only after the user supplies them. Separate
top-offs, water changes, testing, and trimming from “watering.”

## Identity and evidence register

This register controls later research; it does not certify the user's plants.
Reported label text remains verbatim and visually separate from accepted names,
cultivar denominations, and patent status.

| Profile | Current finding | Evidence and unresolved work |
| --- | --- | --- |
| Sedum “Love’s Fire” | *Sedum adolphi* Raym.-Hamet is the accepted spelling surfaced by Plants of the World Online (`https://powo.science.kew.org/results?q=Sedum%20adolphi`); do not normalize the user's “*S. adolphii*” silently. A U.S. plant patent, [USPP37238P2](https://patents.google.com/patent/USPP37238P2/en), names *Sedum adolphi* ‘LOVE'S FIRE’, inventor Renee O'Connell, assignee Altman Specialty Plants, filed 2025-07-09 and granted/published 2026-01-27. Its description says the selection was discovered in 2022 as a mutation of ‘Strawberry’. | The patent makes “PPAF” (plant patent applied for) stale for the patented U.S. cultivar as of 2026-01-27; later copy should use a precisely sourced patent notice if legally/editorially useful. Compare label and whole-plant/detail photos against patent traits before linking this specimen to the patented cultivar. Kew returned HTTP 403 to automated inspection, so confirm its taxon record interactively. |
| Possible *Echeveria* confusion | No authoritative evidence reviewed here establishes an *Echeveria* cultivar named “Love’s Fire” as this plant. Similar retailer/search names are not identity evidence. | Photograph the nursery pot/tag front and back plus rosette, stem, leaf attachment and any flowers. Resolve genus from morphology and provenance rather than search-result imagery. Keep the confusion flag until reviewed. |
| *Kalanchoe humilis* “Desert Surprise” | [RHS](https://www.rhs.org.uk/plants/310184/kalanchoe-humilis-desert-surprise/details) records *K. humilis* ‘Desert Surprise’ in Crassulaceae and describes a compact perennial succulent with patterned fleshy leaves. | Verify the specimen and exact label spelling from photos. The supplied Greg retailer page is inaccessible, so it cannot corroborate the purchase label. Cultivar styling should become ‘Desert Surprise’ only after label/specimen review. |
| Pothos | *Epipremnum aureum* is a provisional identity. [NC State Extension](https://plants.ces.ncsu.edu/plants/epipremnum-aureum/) identifies it as an Araceae climbing/trailing evergreen native to the Society Islands. | “Pothos” covers plants and cultivars that can be confused in trade. Obtain whole vine, nodes, petiole, upper/lower leaf and label photos; record variegation without assigning a cultivar from color alone. |
| Bird of paradise | Common name alone cannot choose between *Strelitzia reginae* and *S. nicolai*. NC State treats [*S. reginae*](https://plants.ces.ncsu.edu/plants/strelitzia-reginae/) as a clumping South African species and [*S. nicolai*](https://plants.ces.ncsu.edu/plants/strelitzia-nicolai/) as a much larger, woody-stemmed species with a different native range. | Keep the page title at genus/common-name level until label, full habit, base/stem, leaf and (if present) flower photos support species identification. A future indoor/outdoor comparison is out of the initial page budget and needs recorded paired conditions. |
| Aquarium hornwort | *Ceratophyllum demersum* is provisional. [Tropica](https://tropica.com/en/plants/plantdetails/?id=4434) describes a rootless *C. demersum* form that may float or be placed at the bottom; this is identifiable-grower guidance, not proof of the specimen or universal aquarium performance. | Obtain package/source and close photographs of nodes, forked leaves and stem. Confirm with a botanical authority before final copy and do not transfer claims about Tropica's particular selection to an unknown specimen. |

### Source and claim rules

- Prefer a botanical authority for accepted name/synonym/family; university
  extension or botanic gardens for broadly supported horticulture; a named
  breeder, patent, label, or identifiable grower for cultivar-specific claims.
- Cite sources at claim level in working data. A retailer listing can document
  a marketed name, but cannot alone verify taxonomy or a user's specimen.
- Separate consensus principles (for example, use an observable water trigger)
  from **suggested starting recipes** and **local adaptations**. Every numeric
  mix, interval, threshold, or tolerance needs a source and applicability note.
- Conflicting sources remain visible in the evidence record with access date,
  exact claim, scope, and resolution status. Do not average incompatible values.
- The two supplied Greg pages—Sedum (`https://greg.app/brand/oasis-labels/sedum-loves-fire-010444/`)
  and Kalanchoe (`https://greg.app/brand/oasis-labels/kalanchoe-humilis-desert-surprise-010315/`)—returned
  HTTP 403 during inspection on 2026-09-14. Their contents remain unverified;
  neither is evidence for identity or care unless later retrieved and assessed.

### Required specimen inputs for final photograph qualification

Before final identity/care review, collect:

- Unedited, well-lit macro and full-habit photographs of every plant; leaf upper
  and lower surfaces, attachment/nodes, stem/base, and flowers or reproductive
  structures if present; ruler/color reference where useful; all label/package
  faces and purchase date/source.
- For both outdoor grow bags: bag dimensions/volume/material, drainage, measured
  sun exposure by time, wind/shelter, slope, current soil/additives and their
  approximate volumes, recent watering/rain history, observed dry-down, and
  seasonal placement. Record current locality separately from prior Pacifica
  context; do not infer a microclimate from city name.
- Indoors: window direction, unobstructed direct-sun hours, distance from glass,
  supplemental-light model/schedule if any, room temperature/humidity range,
  pot dimensions/material/drainage, medium, watering observations, drafts/HVAC,
  and planned outdoor transition conditions for bird of paradise.
- Aquarium: tank volume/dimensions, livestock, temperature, photoperiod and
  fixture/intensity, filtration/flow, substrate and plant placement, fertilizer
  and CO2 use, source water, measured pH/GH/KH/ammonia/nitrite/nitrate as
  available, maintenance history, and hornwort acquisition/behavior.

## Watering-log page contract

Use landscape-like information density within the same US Letter **portrait**
page and safe margins. The table has a narrow left **date/time** column followed
by five plant columns in manifest order. Each plant header contains its short
display name, location marker, and a blank field `Typical interval: ___ days`.
The adjacent printed note reads: “Planning estimate only—check moisture or plant
condition, rain, and season first.” No interval is populated during design.
Use thin dark rules and a pale header tint that remains distinct in grayscale.

Each dated row is one watering event. Every plant cell provides ruled space for
**amount or method** and a **brief observation**; leave a plant's cell blank when
it was not watered. Use at least 0.48-inch row height and approximately 14–16
rows after headers so normal handwriting fits. Sedum and Kalanchoe cells include
a small `Rain/amount: ____` line for handwritten outdoor observations.

Hornwort's header reads `Watering interval: N/A`. Its cells instead accept a
compact aquarium event such as water change/top-off/test/trimming plus amount or
result and observation. The legend must state that aquarium maintenance is not
watering. Do not collapse unrelated tank events into a fictional interval.

## Future implementation and verification contract

### Recommended toolchain

Use **LuaLaTeX** with a small, data-driven document layer (for example,
`expl3`/document commands and a checked-in ordered manifest). It provides exact
physical-page control, mature typography and tables, local OpenType font support,
robust image placement, and deterministic PDF builds without introducing a web
runtime. The Step 06a proof uses LuaLaTeX and distribution-provided TeX Gyre
Pagella and Heros fonts; compilation performs no downloads. The tested
environment was Python 3.12.13, TeX Live 2023 / LuaHBTeX 1.17.0, Pillow 12.3.0,
pypdf 6.18.1, and Poppler 24.02.0. Required commands/packages are `lualatex`,
`pdfinfo`, `pdftoppm`, Pillow, and pypdf. Build the proof with:

```sh
python scripts/build_binder.py --entry sedum-loves-fire --mode draft \
  --output build/binder/sedum-loves-fire-draft.pdf
```

The builder validates catalog schema and selections before compiling, then uses
pypdf independently to enforce one page and a 612 × 792-point MediaBox. Draft
mode visibly permits placeholders; final mode rejects a selected placeholder or
unresolved rights. This foundation does not implement final factual copy, all
species, the care log, combined assembly, CI, or full regressions.

All inputs must be editable text plus local, licensed assets. Bundle permitted
fonts locally with license files (or rely on a pinned distribution), never fetch
assets during the build, and document one clean checkout-to-PDF command and all
required tool versions.

### Manifest and page budgets

Maintain one ordered manifest as the sole assembly authority:

```text
01 sedum-loves-fire       profile       page_budget=1
02 kalanchoe-desert       profile       page_budget=1
03 pothos                 profile       page_budget=1
04 bird-of-paradise       profile       page_budget=1
05 aquarium-hornwort      profile       page_budget=1
06 watering-log           supplemental  page_budget=1
```

The initial combined PDF must contain exactly six pages in that order, and each
profile and supplemental entry must also compile/validate independently against
its one-page budget. Future multipage guides must declare an integer
`page_budget` per manifest entry; changing it requires review of both manifest
and rendered output. A combined total is never allowed to hide one overflowing
entry offset by another missing or blank entry.

### Automation and regression checks

A later GitHub Actions workflow must run for relevant pull requests, changes on
`main`, and `workflow_dispatch`. It builds once from pinned dependencies and
uploads one clearly named, downloadable **combined PDF** artifact. It needs no
credentials, release, publishing service, or deployment.

The validator must fail on:

- a profile or supplemental entry exceeding or missing its declared page budget;
- combined manifest order differing from PDF order, or combined count not six;
- any page MediaBox/CropBox differing from 8.5 × 11 inches (within an explicitly
  documented small point tolerance) or inconsistent rotation;
- unresolved asset/font references, missing required content keys or source
  metadata, placeholder imagery in a release build, or build warnings promoted
  by policy;
- blank/near-blank pages, content outside the safe/content boxes, clipped text,
  overfull boxes, or unintended overflow pages.

Image and content validation must additionally check:

- supported JSON schema versions and duplicate asset IDs;
- every selected asset ID and referenced local file resolving correctly;
- required `alt`, `caption`, `source.photographer`, `source.provenance`, and
  `source.rights` values, with unknowns represented honestly in draft or
  unselected catalog records;
- measured raster format, pixel dimensions and byte budgets, plus effective
  resolution after the rendered crop;
- each adjacent placement comment agreeing with the actual frame definition;
- a visibly labeled Propagation care card on all five summaries;
- replacement of photographs preserving each page budget and combined order;
- omission of optional details producing a clean layout with no empty boxes;
- an overfull image/content combination failing instead of shrinking type,
  removing content, or spilling to a new page; and
- draft placeholders being rejected during final qualification.

Clearly marked draft builds may use explicit placeholders while templates and
content are developed before real photographs arrive. Every asset selected for
final output must document ownership, permission, or a license that permits the
intended use in `source.rights`, and set `source.rights_reviewed` to the boolean
`true` after review. A descriptive rights string alone does not qualify an
asset. Missing, `"unknown"`, pending, or otherwise
unresolved rights must fail final qualification. Draft assets that are not
selected for final output must remain excluded from the PDF; unresolved rights
or review for those unselected records alone do not block final qualification.
These exceptions do not relax catalog schema or duplicate-ID checks. Final
builds also require real, reviewed images and verified identity/care content.
The draft/final mode must be explicit rather than inferred from filenames.

Fixtures must include a deliberately overlong single profile and assert that its
**entry-level pagination** check fails, even if a manipulated combined document
still totals six pages. Also test a reordered manifest, absent image/content
field, wrong page dimensions, inserted blank page, optional-detail omission,
photo replacement, and an overfull image/content combination. Positive tests
assert individual budgets plus combined order/count—not only total page count.

### Human acceptance gates

For every substantive layout or asset change, render all pages to images at a
documented resolution and inspect at 100% plus grayscale for clipping, hierarchy,
body/source readability, photograph focus/crop/resolution, safe and punch
margins, log header clarity, and comfortable handwriting space. Record the
reviewer, build commit, display scale, and findings.

After screen review passes, print on US Letter at actual size (not “fit”), punch
a sacrificial copy, write in several log rows with the intended pen, and inspect
duplex/ink behavior if applicable. Record printer settings and corrections.
Only that later physical check can justify calling the binder print-worthy.

## Deferred decisions

- The approved direction is A typography + B profile layout + H care log. The
  profile foundation is implemented; qualification of final pages and the H
  care log remain pending.
- Final specimen identity, local care values, photographs, and growing/aquarium
  conditions are pending evidence collection and review.
- Actual specimen assets, remaining catalogs/pages, combined assembly, broader
  regression coverage, CI workflow, and generated PDF artifacts remain pending.

### Local verification outputs (Step 06a)

This scoped foundation deliberately does not broaden the repository-wide ignore
policy. Before building locally, add `/build/` and `__pycache__/` as separate
lines in `.git/info/exclude`; this keeps proof PDFs, renders, and Python caches
untracked without changing the shared root `.gitignore`. Broader documentation
and ignore-policy changes are deferred to a follow-up.

Prepared hero and detail crops must exactly match their 1:1 and 41:27 frames.
The builder rejects selected rasters below 240 ppi (792 × 792 hero or 492 × 324
detail), prefers 300 ppi (990 × 990 or 615 × 405), and rejects files above the
1 MiB hard ceiling. Photo preparation attempts a 500 KiB soft goal at acceptable
JPEG quality and reports when it is unmet; failure to meet that soft goal alone
is not an error. Every final selection requires `source.rights_reviewed: true`;
unselected, structurally valid draft records may retain honest unknown rights.
