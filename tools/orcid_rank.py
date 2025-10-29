#!/usr/bin/env python3
# tools/orcid_rank.py — collapse to top K candidates/author, write review CSV + stats
import csv, sys, pathlib, math
from collections import defaultdict

IN = pathlib.Path("citations/_manifests/orcid_candidates.csv")
OUT = pathlib.Path("citations/_manifests/orcid_review.csv")
K = 3  # top-K per author

def norm(s): 
    return " ".join((s or "").strip().lower().split())

def score(row):
    s = 0
    if row.get("orcid"): s += 5
    if norm(row.get("display_name")) == norm(row.get("full_name")): s += 3
    try:
        wc = int(row.get("works_count") or 0)
        s += min(3, wc//50 + 1) if wc>0 else 0
    except: pass
    # small bonus if source is openalex (often richer) or crossref (via DOI)
    src = (row.get("candidate_source") or "").lower()
    if src == "openalex": s += 1
    if src == "crossref": s += 1
    return s

def main():
    rows = []
    with IN.open() as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)

    by_author = defaultdict(list)
    for row in rows:
        by_author[row["author_id"]].append(row)

    reduced = []
    hits, total = 0, 0
    for aid, cand in by_author.items():
        total += 1
        cand.sort(key=score, reverse=True)
        top = cand[:K]
        if any(x.get("orcid") for x in top): hits += 1
        for i, row in enumerate(top, 1):
            row = dict(row)
            row["rank"] = i
            row["match_score_hint"] = str(score(row))
            reduced.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        cols = ["author_id","full_name","rank","match_score_hint",
                "candidate_source","display_name","orcid","works_count","institution"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in reduced:
            w.writerow({k: row.get(k) for k in cols})

    print(f"✅ Wrote {OUT} (top {K} per author)")
    print(f"Authors total: {total}")
    print(f"Authors with >=1 ORCID in top-{K}: {hits} ({hits*100.0/total:.1f}%)")

if __name__ == "__main__":
    sys.exit(main())

