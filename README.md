# aquiloop

MIT-licensed open-source aquarium tools.
Parametric designs in [OpenSCAD](https://openscad.org/) and supporting scripts.

This repo continues the spirit of
[flywheel](https://github.com/futuroptimist/flywheel),
[sugarkube](https://github.com/futuroptimist/sugarkube), and
[sigma](https://github.com/futuroptimist/sigma) with a focus on aquarium gear:
- Lightweight
- Modular
- Reproducible
- Open

## ✨ Tools

### Duckweed Scooper
A narrow, solid-state scooper to quickly remove duckweed from planted aquariums.
Designed to:
- Fit into 10-gallon tanks, even with driftwood, rocks, and plants.
- Be parametric (handle length, scoop width, wall thickness).
- Print cleanly without supports.
- Be extendable to mechanical designs later.

File:
[`tools/duckweed_scooper/duckweed_scooper.scad`](tools/duckweed_scooper/duckweed_scooper.scad)

Render:
`scripts/render_duckweed_scooper.sh` → `stl/duckweed_scooper/duckweed_scooper.stl`

## 📂 Structure
```
aquiloop/
├─ .github/
│  └─ workflows/
│     └─ cad-duckweed-scooper.yml
├─ docs/
│  └─ prompt-docs-summary.md
├─ scripts/
│  └─ render_duckweed_scooper.sh
├─ tools/
│  └─ duckweed_scooper/
│     └─ duckweed_scooper.scad
├─ .gitignore
├─ LICENSE
└─ README.md
```

## 🔄 Workflow
- `scripts/render_duckweed_scooper.sh` renders `.scad` → `.stl` with the OpenSCAD CLI.
- CI runs linting, spellcheck, and smoke tests.
- Contributions follow the same conventions as **flywheel**:
  - Pre-commit hooks
  - Prompt docs
  - Clear commit hygiene

## 🤝 Contributing
- Fork & PR.
- Keep designs parametric and documented.
- Run checks before pushing:
  ```sh
  pre-commit run --all-files
  pytest -q
  ```

## 📜 License
MIT
