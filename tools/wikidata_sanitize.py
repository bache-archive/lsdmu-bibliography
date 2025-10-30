# tools/wikidata_sanitize.py  (drop-in replacement)
#!/usr/bin/env python3
"""
Sanitize citations/_manifests/wikidata_approved.csv down to exactly one
approved, human Wikidata QID per author, with curated overrides.

What this does:
  1) Reads the current approved list (may contain multiple rows per author).
  2) Drops rows that are not clearly "human" or look like orgs/places/artworks.
  3) Applies curated OVERRIDES for tricky names (wins over everything else).
  4) From the remaining rows, picks the single best row per author:
       - lowest 'rank' (1 is best), then prefer a row that has a birth_year.
  5) Normalizes fields and re-writes the CSV in-place.
  6) Saves a backup to _backups/wikidata_approved.csv.bak

Usage:
  python3 tools/wikidata_sanitize.py
"""

from __future__ import annotations
import csv
import pathlib
import re
import shutil
import sys
from collections import defaultdict

APP = pathlib.Path("citations/_manifests/wikidata_approved.csv")
BACKUPS = pathlib.Path("_backups"); BACKUPS.mkdir(exist_ok=True, parents=True)

# Curated, known-correct QIDs for ambiguous authors
OVERRIDE = {
    "grey-alex": "Q725199",        # Alex Grey (visionary artist, 1953–)
    "baring-anne": "Q17333608",    # Anne Baring (British writer, 1931–)
    "berry-thomas": "Q349709",     # Thomas Berry (cultural historian/priest, 1914–2009)
    "clark-w-c": "Q8006273",       # William C. Clark (policy scholar), not zoologist
    "aurobindo-sri": "Q192207",    # Aurobindo Ghosh (Sri Aurobindo)
    "snow-robert": "Q47112345",
    # Add more here if/when you discover recurring ambiguities.
}

# Patterns that indicate a non-person / wrong entity in label/note text
BAD_DESC = re.compile(
    r"(disambiguation|ashram|institute|university|road|marg|artwork|peerage|"
    r"organization|committee|school|press|journal|magazine|museum|college|"
    r"foundation|library|society|department|association|publisher|ashrama|"
    r"trust|company|ltd\.?|llc|corp\.?|inc\.?)",
    re.I,
)

QID_RE = re.compile(r"^Q\d+$")

HEADER = [
    "author_id","full_name","approve","chosen_qid","note",
    "label","rank","birth_year","death_year","is_human"
]

def load_rows(path: pathlib.Path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

def write_rows(path: pathlib.Path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in HEADER})

def is_truthy(v: str) -> bool:
    return str(v).strip().lower() in ("true","1","yes","y")

def sanitize(rows):
    # Normalize and basic validity: keep rows with approve=y and a valid QID + author_id
    rows = [
        r for r in rows
        if str(r.get("approve","")).strip().lower() == "y"
        and r.get("author_id")
        and r.get("chosen_qid") and QID_RE.match(r["chosen_qid"])
    ]

    # Keep humans only (if is_human provided). If missing, keep (lenient).
    def is_human_row(r):
        v = str(r.get("is_human","")).strip()
        return (v == "" or is_truthy(v))
    rows = [r for r in rows if is_human_row(r)]

    # Remove rows with obvious non-person signals in label/note
    def looks_non_person(r):
        text = f"{r.get('label','')} {r.get('note','')}"
        return BAD_DESC.search(text or "") is not None
    rows = [r for r in rows if not looks_non_person(r)]

    # Group by author
    per_author = defaultdict(list)
    for r in rows:
        per_author[r["author_id"]].append(r)

    chosen = []
    for aid, rr in per_author.items():
        # 1) Override wins
        if aid in OVERRIDE:
            q = OVERRIDE[aid]
            picked = next((x for x in rr if x.get("chosen_qid") == q), None)
            if not picked:
                # synthesize a minimal approved row using first entry's name/label if present
                first = rr[0]
                picked = {
                    "author_id": aid,
                    "full_name": first.get("full_name",""),
                    "approve": "y",
                    "chosen_qid": q,
                    "note": "manual override",
                    "label": first.get("label",""),
                    "rank": "1",
                    "birth_year": first.get("birth_year",""),
                    "death_year": first.get("death_year",""),
                    "is_human": "True",
                }
            else:
                picked["approve"] = "y"
                picked["is_human"] = "True"
            chosen.append(picked)
            continue

        # 2) Otherwise pick best by rank (ascending), then prefer with a birth_year
        def sort_key(x):
            try:
                rnk = int(str(x.get("rank","")).strip() or "999999")
            except ValueError:
                rnk = 999999
            by = str(x.get("birth_year","")).strip()
            prefer_birth = 0 if by else 1
            return (rnk, prefer_birth)
        rr.sort(key=sort_key)
        best = rr[0].copy()
        best["approve"] = "y"
        best["is_human"] = "True"
        if not best.get("rank"):
            best["rank"] = "1"
        chosen.append(best)

    # Normalize to single row per author, stable order by author_id
    chosen.sort(key=lambda r: r["author_id"])
    out = []
    seen = set()
    for r in chosen:
        aid = r["author_id"]
        if aid in seen:
            continue
        seen.add(aid)
        o = {k: r.get(k,"") for k in HEADER}
        o["approve"] = "y"
        o["is_human"] = "True"
        o["rank"] = str(o.get("rank","")).strip() or "1"
        out.append(o)

    return out

def main():
    if not APP.exists():
        print(f"ERROR: {APP} not found", file=sys.stderr)
        sys.exit(1)

    # Backup before modifying
    bkp = BACKUPS / "wikidata_approved.csv.bak"
    shutil.copy2(APP, bkp)
    print(f"Backup written → {bkp}")

    rows = load_rows(APP)
    before = len(rows)
    cleaned = sanitize(rows)
    write_rows(APP, cleaned)
    print(f"Sanitized {before} → {len(cleaned)} rows (1 per author).")

    # quick spot checks
    for aid in ("grey-alex","baring-anne","berry-thomas","clark-w-c","aurobindo-sri"):
        hits = [r for r in cleaned if r["author_id"] == aid]
        if hits:
            print(f"{aid:>18}: {hits[0]['chosen_qid']}  {hits[0]['label'] or ''}")

if __name__ == "__main__":
    main()