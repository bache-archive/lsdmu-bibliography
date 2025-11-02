#!/usr/bin/env python3
"""
Validate that all Bache-authored CSL-JSON entries add OpenAlex exactly where intended.

Checks:
  1) For any author[i] where author[i].x-bache.wikidata == "Q112496741",
     ensure author[i].x-bache.openalex == "A5045900737".
  2) Warn if any author[i].x-bache.openalex == "A5045900737" is present
     WITHOUT wikidata == "Q112496741" (misapplied OpenAlex).
  3) Fail if any *.tmp files exist in the bib/ directory.
Exit code:
  0 on success; 1 if any errors; non-fatal warnings are printed but do not fail.
"""

import json
import pathlib
import sys

BIB_DIR = pathlib.Path("citations/source/bache/LSDMU/bib")
BACHE_QID = "Q112496741"
BACHE_OPENALEX = "A5045900737"

errors = []
warnings = []

# (3) No temp files
tmp_files = list(BIB_DIR.glob("*.tmp"))
if tmp_files:
    errors.append(f"Found stray tmp files: {', '.join(str(p.name) for p in tmp_files)}")

# Scan JSON files
for f in sorted(BIB_DIR.glob("*.json")):
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"{f.name}: JSON parse error: {e}")
        continue

    authors = data.get("author") or []
    if not isinstance(authors, list):
        warnings.append(f"{f.name}: 'author' is not a list (skipping author-level checks)")
        continue

    # Track whether this file had any Bache author objects
    bache_hits = 0

    for idx, a in enumerate(authors):
        if not isinstance(a, dict):
            continue
        xb = a.get("x-bache") or {}
        if not isinstance(xb, dict):
            continue

        qid = xb.get("wikidata")
        oa  = xb.get("openalex")

        if qid == BACHE_QID:
            bache_hits += 1
            if oa != BACHE_OPENALEX:
                errors.append(
                    f"{f.name}: author[{idx}] has wikidata={BACHE_QID} but openalex is {repr(oa)}"
                )
        # Inverse safety check: if OpenAlex matches Bache but QID doesn't, warn
        if oa == BACHE_OPENALEX and qid != BACHE_QID:
            warnings.append(
                f"{f.name}: author[{idx}] has openalex={BACHE_OPENALEX} without wikidata={BACHE_QID} (qid={repr(qid)})"
            )

    # Optional: nudge if no Bache author present but filename is clearly a Bache work
    # (Not an error, just a heads-up if you expect Bache as author.)
    if f.name.startswith("bache-") and bache_hits == 0:
        warnings.append(f"{f.name}: filename suggests Bache, but no author.x-bache.wikidata={BACHE_QID} found")

# Report
if warnings:
    print("WARNINGS:")
    for w in warnings:
        print("  -", w)
    print()

if errors:
    print("ERRORS:")
    for e in errors:
        print("  -", e)
    sys.exit(1)

print("✅ Validation passed: OpenAlex added correctly for all Bache author entries; no stray .tmp files.")
