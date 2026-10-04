# Cherry shrimp binder extension

K221, 2026-10-04. Daniel selected cherry shrimp, **Neocaridina davidi**, after
the [options comparison](shrimp-options-20-gallon.md). This selects a species
for planning; it does not document acquired animals or authorize stocking.
The optional 10-gallon shrimp-only nursery has unknown cycling status. Later
adult transfers to the reported 20-gallon Kuhli tank remain conditional.

## Evidence and care decisions

The [entry bibliography](../../binder/entries/cherry-shrimp/sources.yaml) records
eight sources inspected on 2026-10-04. Thirty scoped claims separate published
guidance, proposed applications and unknowns. UF/IFAS supplies identity, direct
development and invasion context; veterinary guidance supplies general aquarium
water and medication cautions. Experienced sellers supply practical husbandry,
not controlled predation trials or a guaranteed home breeding protocol.

- Eggs hatch into miniature freshwater shrimp. Do not import Amano saline larval
  care. UF/IFAS's 16-19-day incubation and Co-Op's approximately one month are kept
  separate. The extension's approximately 30-day maturity is not a home deadline;
  its underlying full research paper was not inspected.
- Published broad ranges, preferred temperature and hardness minima retain their
  meanings. The Shrimp Farm's narrower chemistry is attributed separately. No
  universal nitrate ceiling, remineralization recipe, lifespan, stocking density
  or predation-safe transfer size is invented.
- GH and KH are different tests. The GH/KH source articles are used only for those
  distinctions, not their simplified physiology or contradictory CO2 explanation.
- The nursery needs documented fishless cycling, stable prepared water, mature
  grazing surfaces, protected intakes and observed food access. A tank's age or
  one zero reading is not proof of processing capacity. Do not test readiness
  using live shrimp or chase parameters through abrupt changes.
- The possible shared temperature interval is explicitly derived from two trade
  guides. Actual Kuhli identity, shared chemistry, tank footprint, full stocking
  and treatment history remain unresolved. Adult coexistence cannot establish
  juvenile or post-molt safety. The nursery is not also a fish quarantine.
- Hornwort/guppy grass and optional moss are a habitat proposal. Plant entries,
  attachment methods, category accents and any binder rename are separate work.

## Controlled assembly

This branch depends on Kuhli PR #109 at `7cc7f6450b818de90d94e72be8f537ec60fc4de6`.
While that PR is unmerged, this PR targets its branch; do not merge out of order.
The opt-in `manifest-v4.yaml` preserves the first eighteen pages and inserts
cherry shrimp care, tank setup and reproduction as pages 19-21, moving the
unchanged watering log to page 22 as Daniel requested. Existing
manifests, all prior entries, shared templates and dependencies remain unchanged.
Reuse the animal schema and renderer without a second species-specific engine.
No photographs or assets are fabricated. Draft-only publication gates remain.

```sh
python -m unittest discover -s tests/binder -v
python scripts/build_binder.py --manifest binder/manifest-v4.yaml --mode draft --output build/binder/aquiloop-binder-shrimp-draft.pdf
```

CI builds the 22-page draft and 150-DPI color/grayscale proofs. Focused tests cover
canonical append order, claim resolution, pages, links, safe text/paint bounds
and pixel-identical inherited pages in both modes. Inspect all three new pages
and compare inherited proofs with #109's accepted artifact before handoff.
Final exact-head artifact hashes and comparison evidence are recorded in the PR.
Six- and sixteen-page baseline proofs remain part of CI. K161 physical print,
punch and handwriting acceptance is still pending. No live changes or merge.

## Owner photograph

Daniel committed and explicitly authorized `assets/overview.jpg` on main on
2026-10-04. The selected `cherry-overview-001` catalog record documents that
permission. The existing text-only placeholder remains an unselected fallback.
Follow [binder photo policy](../../binder/AGENTS.md): only owner photographs;
no stock or AI-generated substitutes, generative fill or composites.

The actual photo was visually inspected: a red shrimp among plants, without
camera-roll UI or personal text. It is a square 990 x 990 RGB JPEG, matching the
3.30-inch hero slot at 300 ppi, with no additional crop or visual processing.
The photo supports an owner specimen reference, not an independent taxonomic
determination or current stocking measurement. Its original SHA-256 was
`bb7b8ec0d01c4ed7f1b2ef1f8441ffeade98806b6b8fef9ffc5ebdc9aac14e95`.
Removal of nonessential EXIF/XMP segments without recompression produced
`66fd7e4938b777a6d3df2e1177ac6ed6479fe9f43fc7b1055d1ea4953f6dc20d`;
decoded RGB pixels are identical. There is no embedded ICC profile, so verified
sRGB is not claimed and no color conversion was performed.


The sRGB export specification was requested, not verified in the supplied JPEG.
The binder policy explicitly permits this authorized untagged owner photo in
draft proofs while preserving its pixels. No source profile is known, so merely
assigning sRGB would not verify its original color interpretation. The photo is
not certified for color-managed print output: obtain a known-profile owner export
and complete physical color acceptance before making that claim. Existing screen
color/grayscale proof review establishes layout/readability only. This resolves
review #110 discussion_r4179545053 through an explicit draft policy clarification,
without changing image bytes, rendering, or the user's photograph.
