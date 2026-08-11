#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $(basename "$0") tools/<part>/<name>.scad" >&2
  exit 1
fi

scad_file=$1
if [[ ! -f "$scad_file" ]]; then
  echo "File not found: $scad_file" >&2
  exit 1
fi
case "$scad_file" in
  *.scad) ;;
  *)
    echo "Expected .scad file: $scad_file" >&2
    exit 1
    ;;
esac

# Mirror the source's path under tools/ into stl/ and obj/, e.g.
# tools/duckweed_scooper/duckweed_scooper.scad ->
#   stl/duckweed_scooper/duckweed_scooper.stl
#   obj/duckweed_scooper/duckweed_scooper.obj
rel=${scad_file#tools/}
name=${rel%.scad}
stl_path="stl/${name}.stl"
obj_path="obj/${name}.obj"

mkdir -p "$(dirname "$stl_path")" "$(dirname "$obj_path")"

if [[ -z "${DISPLAY:-}" ]]; then
  xvfb-run -a openscad -o "$stl_path" "$scad_file"
else
  openscad -o "$stl_path" "$scad_file"
fi

# OBJ export isn't available in the OpenSCAD build shipped by Ubuntu's apt
# repo, so convert the rendered STL with assimp instead of relying on
# OpenSCAD's own (newer-only) --export-format=obj.
assimp export "$stl_path" "$obj_path" >/dev/null
