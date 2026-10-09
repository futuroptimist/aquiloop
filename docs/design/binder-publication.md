# Publishing the care binder to Slack

The binder workflow prepares the latest **41-page succulent draft** from
`binder/manifest-v7.yaml` for native file upload to **#automation**
(`C0C8T7FDAAC`) in workspace `T0C80NYUHHP`. This implements Daniel's request
in #aquiloop (`C0C7TGSCSP7`) on 2026-10-09. The older 6-, 16-, 19-, 22-, and
31- and 35-page review artifacts remain available in the build.

## Owner setup — disabled until explicitly enabled

No live Slack integration is enabled by this change. Inspection of repository
secret **names only** found no binder Slack credential. No secret values were
accessed, no app was registered, and no PDF was posted while preparing this PR.

An owner must choose an approved Slack bot in the workspace, with only
`files:write` and `files:read`, and add it to #automation. The owner enters its
bot token as the repository Actions secret **`BINDER_SLACK_BOT_TOKEN`** using
GitHub's UI, then sets the repository Actions variable
**`BINDER_SLACK_PUBLISH_ENABLED=true`** when ready to enable posting. Never put
the token in chat, source code, a command argument, or a review comment.
No incoming webhook, `chat:write`, channel-history scope, or public-file URL is
needed. If an existing bot already has these permissions and membership, only
the secret and enable variable are needed. No permissions or settings were
changed as part of implementation.

GitHub's built-in job token receives `contents:write` only in the gated publish
job, to maintain the `binder-publication-state` branch. The publisher creates
that branch from the first source commit and writes only `publication.json`.
Repository rules must permit that operation. Do not relax protections on main.
The checkpoint is non-secret: commit/run provenance, content and byte digests,
Slack file ID, status and optional last-checked commit. Keep the state branch;
deleting or resetting it loses duplicate protection. It is not a deployment.

## Build and trust boundary

Only a successful `push` build of this repository's default branch `main` can
publish. PRs, forks and manual builds cannot enter the publishing job. This
covers merges (including squash and rebase merges) and authorized direct main
pushes; branch protections remain responsible for requiring PR merges.
No `workflow_run`, `pull_request_target`, cross-run artifact selection, or
untrusted artifact script execution is used. All third-party actions are pinned
to commit SHAs, checkouts do not persist credentials, and runtime API requests
refuse redirects and avoid logging credentials, signed URLs or response bodies.

The existing build and its page validation/rendering must finish successfully
before packaging a publication candidate. A downstream job downloads the
candidate from **the same workflow run**, verifies repository, source SHA, run
ID, page-count declaration, PDF filename/header and exact byte SHA-256 against
the provenance manifest, then uploads that PDF. It does not rebuild the binder.
The manifest and Slack initial comment identify the source commit, run URL,
exact PDF digest and content fingerprint. The candidate artifact is retained
for 14 days. Retry the publish job within that period; expired artifacts require
a new successful main push build. A rerun of only the publish job may have a
later run attempt than the build: the original build attempt stays in provenance.

Failed regression, build, validation, render or artifact steps prevent posting.
The existing pinned Ubuntu snapshot and signature checks are unchanged; snapshot
HTTP 503 failures block the PDF prerequisite and must not be bypassed.

## What counts as a content change

`aquiloop-rendered-binder-v1` hashes the ordered RGB pixel bytes of pinned Poppler
150-DPI color proofs, extracted page text and URI link targets. It reuses the
v6 log proofs for pages 31–35 and renders pages 1–30 from that same validated
v7 PDF; it never substitutes another edition's proofs or rebuilds the PDF.
It checks 41 ordered proof pages, Letter media/crop boxes and zero rotation.
PDF timestamps, document IDs, compression, object numbering and PNG container
metadata do not affect this digest. Changes to visible proofs, extracted text,
link destinations or page ordering do. Unsupported interactive destinations
fail closed. This is a print-content fingerprint, not a full PDF semantic
equivalence test: subpixel changes invisible at 150 DPI and non-rendered PDF
features are outside its definition. A renderer/toolchain change can cause a
new publication even when source content is unchanged.

First enablement publishes the next successfully built candidate. An unchanged
candidate advances the last-checked commit without posting. A subsequent real
reversion (A → B → A) publishes again. Older completed builds are skipped when
their commit is behind the checkpoint; divergent history requires owner review.

## Retry and duplicate protection

One publisher runs at a time, with a ten-minute timeout and a bounded queue of
up to 100 pending jobs (`queue: max`, no cancellation of the running job).
If builds complete out of order, a stale PDF never replaces a newer one.
Queue overflow and stale builds are intentionally not backfilled automatically.

1. Allocate a Slack file and upload bytes privately.
2. Save its file ID and provenance as `pending` with GitHub Contents API
   compare-and-swap protection. An unsuccessful checkpoint write aborts sharing.
3. Complete that **same file ID** into #automation, then save `published`.
4. On retry, reconcile a pending ID with `files.info` before allocating anything
   new. If already shared to #automation, save success; otherwise attempt the
   one-shot completion of the same ID. Never allocate a replacement while a
   pending checkpoint remains unresolved.

Slack documents that
[`files.completeUploadExternal`](https://docs.slack.dev/reference/methods/files.completeUploadExternal/)
can only be called once per upload. This is the duplicate barrier if completion
succeeded but the response or final GitHub write was lost. A failure before the
checkpoint can leave a private, uncompleted upload; it cannot leave a channel
post. HTTP errors and rate limits stop the job, without blind mutation retries.
Rerun the failed publish job after service recovery; 45-second request timeouts
and the job timeout bound each attempt.

If Slack cannot report a pending file (expired upload, eventual consistency,
permission problem, or ambiguous completion), the job stops for owner
reconciliation. Retry later first. The owner must verify that file's actual
channel share before correcting a checkpoint. Mark a confirmed share published;
only clear a pending upload after confirming it was never shared. Do not delete
the ledger, blindly reset to an old commit, or repost a replacement as a retry.
This deliberately favors avoiding duplicates over automatic recovery from an
unresolvable Slack response. No live upload test is part of CI.

## Why native upload

Native upload gives channel readers a preview and downloadable PDF, subject to
workspace file retention. It requires the two file scopes and a small durable
checkpoint. A GitHub Actions artifact link expires after 14 days and can require
GitHub access, so it does not satisfy durable delivery. A release-asset link
could be durable but would add public release management and still need a
separate Slack message idempotency protocol. Native upload best matches this
request without publishing releases or public file URLs.

Run tests with `python -m unittest discover -s tests/publication -v` using the
existing pinned binder requirements. The publication test job runs independently
of Ubuntu APT so snapshot outages do not conceal its result. Tests use synthetic
PDFs/proofs and fake services; they never contact Slack or GitHub.
