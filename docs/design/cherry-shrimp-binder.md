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

This branch depends on Kuhli PR #109 at `4dc205014ab4b14e5c5fed964fb515a3da8567a9`.
While that PR is unmerged, this PR targets its branch; do not merge out of order.
The opt-in `manifest-v4.yaml` preserves the nineteen-page manifest verbatim and
appends cherry shrimp care, tank setup and reproduction as pages 20-22. Existing
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
The accepted nineteen-page PDF SHA-256 is
`251e9c85d4305513f93f96e2017bf0dd785133160ab8f2a3e9fa3ed7f441c8cc`.
Six- and sixteen-page baseline proofs remain part of CI. K161 physical print,
punch and handwriting acceptance is still pending. No live changes or merge.
