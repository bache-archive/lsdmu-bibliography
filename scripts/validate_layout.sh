#!/usr/bin/env bash
set -euo pipefail
nested="citations/source/bache/LSDMU/bib/source/bache/LSDMU/bib"
if [ -d "$nested" ]; then
  echo "ERROR: Nested bib directory detected at: $nested" >&2
  exit 1
fi
