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
  tools/*.scad) ;;
  *)
    echo "Expected a .scad file under tools/: $scad_file" >&2
    exit 1
    ;;
esac
case "$scad_file" in
  *..*)
    echo "Refusing path with '..' segment: $scad_file" >&2
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
  render_cmd=(xvfb-run -a openscad -o "$stl_path" "$scad_file")
else
  render_cmd=(openscad -o "$stl_path" "$scad_file")
fi

if output=$("${render_cmd[@]}" 2>&1); then
  printf '%s\n' "$output"
else
  printf '%s\n' "$output" >&2
  # Shared/library sources (e.g. parameters.scad, lib/common.scad) have no
  # top-level geometry of their own and are meant to be included by other
  # files, not rendered directly, so skip them instead of failing the job.
  if printf '%s\n' "$output" | grep -q "Current top level object is empty."; then
    echo "Skipping STL/OBJ export for empty model: $scad_file" >&2
    rm -f "$stl_path"
    exit 0
  fi
  exit 1
fi

# OBJ export isn't available in the OpenSCAD build shipped by Ubuntu's apt
# repo, so convert the rendered STL with assimp instead of relying on
# OpenSCAD's own (newer-only) --export-format=obj.
assimp export "$stl_path" "$obj_path" >/dev/null
