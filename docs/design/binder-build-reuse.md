# Disposable binder build reuse (K-330)

## Boundary

Reuse is opt-in through `--reuse-session`. The default builder API, all existing
regression tests (including negative, mutation, historical-build and determinism
tests), and layout diagnostics remain cold. The workflow creates a fresh session
only after the complete regression gate passes. No test is skipped or weakened.
The dedicated reuse tests explicitly create their own temporary sessions.

`binder_reuse.py init` creates a unique directory under `RUNNER_TEMP`. Its owner
is the repository, run ID, run attempt and job ID. Another job or retry cannot
open the session. Nothing is restored through Actions cache, uploaded as a cache,
or shared with the publication job. Existing dependency caching is unchanged.

## Compiled pages

Each lookup includes all binder files, builder/helper source, dependency pins,
the selected asset records and files, generated TeX buffers, page options,
fixed source-date environment and compiler arguments/pass count. The toolchain
identity includes executable/shared-library bytes, versions, Python runtime and
package trees, full TeX/font/configuration search trees, and relevant environment
variables. Keys use file-content SHA-256. Within one process, Linux hashes may be
reused only while device, inode, size, mtime and ctime all match, and ctime is more
than one second old (recent files are rehashed to avoid same-tick stat races).
Linux ctime makes same-size edits with restored mtime visible; other platforms rehash bytes. A file
changing during hashing fails explicitly. This hash memo is never persisted.
Every lookup still walks the trees, so new search-tree files/directories and
symlink targets affect the key. Unsupported custom search
path expressions fail explicitly rather than silently omitting inputs.

Input/rights/evidence resolution still runs before lookup. Reused PDFs still pass
the normal page geometry/text/identity and assembly checks. A cold reusable build
uses LuaLaTeX's recorder; external inputs in its `.fls` file are also checked by
content hash on subsequent hits. Only a successfully validated PDF is stored.
The recorder does not change the document content or requested compiler passes.

## Raster proofs

The proof wrapper keeps the existing Poppler options, ranges, filenames and PNG
format. Its key contains a complete serialized single-page object/resource graph,
rendering options, helper code and toolchain identity. A miss rasterizes the
original complete PDF with the requested single-page range. It does not rasterize
the normalized key document. Color and grayscale/DPI options have distinct keys.

Only the binder's simple `/Type` + `/Pages` catalog is eligible. Forms, optional
content, output intents, names and other catalog additions take the original
cold rendering path. Every cached payload is verified against its recorded
SHA-256; corrupt or missing payloads are misses. A partial write cannot be a hit.
The existing publication fingerprint and all historical proof-count checks remain.

## Measurement and equivalence

Baseline main run: [38305415429](https://github.com/futuroptimist/aquiloop/actions/runs/38305415429),
commit `967fa79ad1e7667220632e9e437e3b69f7f2aeba`, pinned Ubuntu/Python/TeX/Poppler.
The build job took **34m43s**, regression **19m03s**, and production build/proof
stages **12m43s**. Dependency caching already hit. These are measured wall-clock
stages, not CPU benchmarks; runner/network differences can affect comparisons.

Run-specific candidate measurements, CI links and complete artifact comparisons
are recorded in [PR #122](https://github.com/futuroptimist/aquiloop/pull/122).
The unchanged cold regression stage remains a deliberate performance floor.
Acceptance requires exact-head CI, actual reuse hits, unchanged PDF/proof outputs
and in-scope review findings resolved; a cache hit alone is not evidence of a
net speedup. Reporting new run measurements does not require changing build inputs.
