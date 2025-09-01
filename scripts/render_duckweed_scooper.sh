#!/usr/bin/env bash
set -euo pipefail
mkdir -p stl/duckweed_scooper
if [[ -z "${DISPLAY:-}" ]]; then
  xvfb-run -a openscad -o stl/duckweed_scooper/duckweed_scooper.stl \
    tools/duckweed_scooper/duckweed_scooper.scad
else
  openscad -o stl/duckweed_scooper/duckweed_scooper.stl \
    tools/duckweed_scooper/duckweed_scooper.scad
fi
