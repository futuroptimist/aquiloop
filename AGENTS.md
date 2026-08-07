# Repository guidance

- Keep changes small and preserve the existing repository layout.
- Put authoritative design documents in `docs/design/`.
- Keep printable designs parametric: commit editable OpenSCAD source under `tools/` and treat STL files as generated artifacts.
- Do not commit generated meshes, credentials, or unrelated dependency changes.
- Run `git diff --check` and any relevant repository checks before committing.
