#!/usr/bin/env bash
set -euo pipefail
mkdir -p stl/duckweed_scooper
openscad -o stl/duckweed_scooper/duckweed_scooper.stl tools/duckweed_scooper/duckweed_scooper.scad
