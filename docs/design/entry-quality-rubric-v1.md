# Unified plant and animal entry quality rubric v1

Frozen 2026-10-11. Canonical observable tests: `binder/audit/rubric-v1.json`.
This grades documented usefulness, completeness, evidence integrity and validation,
not desirability, ease, productivity or habitat readiness. Each of 40 subchecks
passes for 2.5 points or fails for zero. No impression-based partial awards.

## Evaluation rules

Cite a source path/claim or exact PDF page for every pass. Give a concrete reason
and next step for every failure. Unknown is not N/A and does not earn facts credit
unless that test expressly permits an unknown or justified no-protocol treatment.
Functional equivalents apply (water for fish, soil/media for terrestrial plants).
Reproduction is never wholly N/A because breeding is unwanted or difficult;
biological feasibility and a justified safe observation-only path can satisfy it.
N/A requires biological irrelevance, a concrete reason and reviewer sign-off.
Identity, safety, evidence, imagery and final-PDF tests can never be N/A.
A missing owner image is a V1b failure, not biological irrelevance.

Score = round-half-up(100 * earned / applicable points). Retain earned and
applicable points in increments of 2.5 and publish the denominator. Record raw
and effective integers separately; retain normalized percentage to one decimal internally. A confirmed content safety/accuracy failure
caps effective score at 49 (REQUIRES CORRECTION); pending verification caps it
at 69 (UNVERIFIED). Passing gates do not imply habitat or print readiness.

Critical content failures: unsupported identity that changes care; incorrect
units or dangerous chemical/thermal targets; unsubstantiated breeding induction
or habitat-ready assertions; ecological escape/release advice or unsupported
legal permission; guaranteed stocking/cohabitation/juvenile survival; hidden
material contradictions, fabricated evidence/observations/rights, unauthorized
imagery; a PDF that omits or obscures an essential warning. An honestly gated
unknown is not a failure. A labeled photo placeholder loses V1b only.

## Evidence and readiness

Keep publication/version, last content inspection, last successful URL check,
and next-review trigger separate. HTTP success is not content inspection.
Record failed refreshes honestly; preserve traceable earlier evidence. Stable
biology has no automatic expiry. Revisit changed/high-consequence claims during
each substantive edition, current legal/program constraints before action,
and mutable practical-care pages annually as a documentation maintenance default.
The shrimp ovarian-development versus embryo-carrying correction is the
regression case: institutional summaries can still oversimplify.

Keep readiness as a separate nonnumeric checklist: identity/source, actual
habitat, measured water/conditions, safety, capacity/surplus and authorization.
An unready habitat blocks action, not the score of an honest planning entry.
Physical print, color, punch and handwriting acceptance stay pending unless
actually performed. Scores authorize no stocking, breeding, transfer, merge,
release, publication or deployment.

## Record contract

`python scripts/binder_audit.py REPORT.json --pdf PROOF.pdf` validates record structure, exact
manifest coverage, score arithmetic, gate caps and traceable evidence fields.
It does not verify biology, rights, source truth or visual quality automatically.
Records contain entry ID, working name/status, rubric version, source commit,
manifest, PDF SHA-256, audit date, actual pages and section names, all forty
outcomes, earned/applicable totals, raw/effective scores, gate state/evidence,
N/A reviewer reasons, material unknowns and top improvements. Evidence links
must resolve within the checkout or name an exact PDF page; source snapshots
are hashed to bind the evidence inventory. Final-head CI and inspection evidence
belong in the report, not in fictional passing fixtures.

Reports are sidecars: never embed a PDF hash in that same PDF. Generate them
after the final content commit and preserve prior sidecars when scores change.
No actual private habitat values, approval data or household details belong in
public audit fixtures. Use synthetic data in tests.

The audit CLI requires a clean checkout, including no staged, unstaged or
untracked inputs, and every source snapshot must be Git-tracked. Keep generated
PDFs and report sidecars in an ignored output directory or outside the checkout;
ignored output alone does not invalidate committed-source provenance.

Each cited snapshot also must match the blob at the recorded commit after Git
clean conversion (including configured line endings). This catches modified
snapshots hidden by assume-unchanged or skip-worktree index flags.

The canonical rubric and selected manifest are mandatory source snapshots.
Each entry repeats the report's rubric, commit, manifest, PDF digest and audit
date, and the validator rejects missing or contradictory entry provenance.
