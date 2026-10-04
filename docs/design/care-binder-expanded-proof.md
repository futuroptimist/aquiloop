# Expanded binder digital proof

Digital proof date: 2026-10-04. This is a draft, not final botanical or physical
print acceptance. Review order is foundation PR #106, then companion-pages PR
#107, which is stacked on the foundation branch. Neither PR is merged here.

## Acceptance evidence

The rendered source commit is `2e38194e8a04a252dbe93150a0c3de59b02e2179`.
[Binder CI run 37184175798](https://github.com/futuroptimist/aquiloop/actions/runs/37184175798)
passed all 70 regression tests with no skipped tests, built the original six-page
draft and all ten individual companions, and assembled the sixteen-page draft.
The ordinary linkcheck and shellcheck jobs also passed on that commit.

Download the run's `aquiloop-binder-expanded-proof` artifact for the PDF and
150-DPI color and grayscale PNGs of all sixteen pages. Artifacts expire after
14 days; the committed sources and workflow reproduce them. The reviewed PDF
SHA-256 is:

```text
e6c124bc72de9844814d793827880b129ba6cb8dfcb17f20deeb8260fb0f454f
```

All ten final companion pages were visually inspected in color and grayscale
at 150 DPI. The six overview/log pages were also visually inspected in both
modes; their final CI PNG hashes equal the previously inspected proof exactly.
Text, citations, recipe and milestone tables, the pothos vector schematic,
writing fields, and white margins remain legible without clipping or overlap.

Automated checks cover canonical order, one Letter page per entry/kind,
MediaBox/CropBox and rotation, text and painted-content safe bounds, white
backgrounds, reference resolution, exact recipe arithmetic, rejected two-page
companions, and unchanged overview/log text and photo geometry except explicit
v2 page-kind labels. Existing overview sources, photographs, catalogs, research
worksheets, shared Pacifica context, v1 manifest, and dependencies are unchanged.

Reproduce using the pinned repository CI environment:

```sh
python -m unittest discover -s tests/binder -v
python scripts/build_binder.py --manifest binder/manifest.yaml --mode draft --output build/binder/aquiloop-binder-draft.pdf
python scripts/build_binder.py --manifest binder/manifest-v2.yaml --mode draft --output build/binder/aquiloop-binder-expanded-draft.pdf
```

The Windows LuaLaTeX installation could not render because luaotfload could not
load `lua-uni-case`. No installer or global configuration was changed. The
successful pinned Linux CI builds supplied the PDFs inspected locally with the
existing Poppler installation.

## Remaining gates and uncertainties

- The research stage already merged through PRs #97, #100, and #104 was reused,
  including 193 scoped claims; this implementation does not duplicate research.
- Ledger stages 15-19 have implementation and digital proof evidence. Stage 20
  still requires PR review and authorized merge. Stage 21 requires checking the
  subsequent main-branch artifact. Stage 22 requires the owner's physical print
  proof; no printing or physical plant action occurred.
- Specimen identities remain provisional. Strelitzia reginae and S. nicolai
  recommendations remain distinct; cultivar identity, household exposure,
  substrate composition, tank measurements, and universal lifespans are not
  invented. ZIP-majority climate context is not a yard measurement.
- Proposed mixtures and observation-based transfer checks remain labeled.
  Establishment media, established-plant recipes, germination, rooting,
  flowering, and lifespan remain separate concepts. Hornwort remains rootless
  aquatic guidance without a terrestrial recipe.
- Final-mode publication and optional companion photographs remain unavailable;
  the current companions use native text, rules, tables, and a vector schematic.
