# tools/wikidata_sanitize.py
#!/usr/bin/env python3
import csv, pathlib, re, shutil, sys
from collections import defaultdict

APP = pathlib.Path("citations/_manifests/wikidata_approved.csv")
BACKUPS = pathlib.Path("_backups"); BACKUPS.mkdir(exist_ok=True, parents=True)

# Curated, known-correct QIDs for ambiguous authors
OVERRIDE = {
    "grey-alex": "Q725199",        # Visionary artist (1953–)
    "baring-anne": "Q17333608",    # British writer (1931–)
    "berry-thomas": "Q349709",     # Cultural historian / priest (1914–2009)
    "clark-w-c": "Q8006273",       # William C. Clark (policy scholar), not zoologist
    "aurobindo-sri": "Q192207",    # Aurobindo Ghosh
    # If you want the philosopher/editor McDermott, uncomment next line:
    # "mcdermott-robert": "Q7346315",
}

# Patterns that indicate a non-person / wrong entity in label/note text
BAD_DESC = re.compile(
    r"(disambiguation|ashram|institute|university|road|marg|artwork|peerage|"
    r"organization|committee|school|press|journal|magazine|museum|college|"
    r"foundation|library|society|department|association|publisher)",
    re.I
)

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

def sanitize(rows):
    # 1) keep approved rows only
    rows = [r for r in rows if str(r.get("approve","")).lower() == "y"]

    # 2) keep humans only (is_human True/1/yes) when present; else keep (be lenient)
    def is_human_flag(r):
        v = str(r.get("is_human","")).strip().lower()
        return (v in ("true","1","yes",""))  # empty treated as unknown -> keep
    rows = [r for r in rows if is_human_flag(r)]

    # 3) remove rows with obviously non-person signals (in label/note)
    def bad_label(r):
        text = f"{r.get('label','')} {r.get('note','')}"
        return BAD_DESC.search(text or "") is not None
    rows = [r for r in rows if not bad_label(r)]

    # 4) group by author, apply overrides or pick best (lowest rank; prefer ones with birth_year)
    per_author = defaultdict(list)
    for r in rows:
        per_author[r["author_id"]].append(r)

    chosen = []
    for aid, rr in per_author.items():
        # Override wins (even if not present in rr, we synthesize a row)
        if aid in OVERRIDE:
            q = OVERRIDE[aid]
            picked = next((x for x in rr if x.get("chosen_qid") == q), None)
            if not picked:
                # synthesize a minimal approved row using first entry’s name
                picked = {
                    "author_id": aid,
                    "full_name": rr[0].get("full_name",""),
                    "approve": "y",
                    "chosen_qid": q,
                    "note": "manual override",
                    "label": "",
                    "rank": "1",
                    "birth_year": "",
                    "death_year": "",
                    "is_human": "True",
                }
            else:
                picked["approve"] = "y"; picked["is_human"] = "True"
            chosen.append(picked)
            continue

        # Otherwise, sort by rank (asc), then prefer with birth_year present
        def sort_key(x):
            rnk = x.get("rank"); 
            try: rnk = int(rnk)
            except: rnk = 999999
            by = x.get("birth_year")
            return (rnk, 0 if (by and str(by).strip()) else 1)
        rr.sort(key=sort_key)
        best = rr[0]
        best["approve"] = "y"; best["is_human"] = "True"
        chosen.append(best)

    # Normalize header fields for all rows
    out = []
    for r in chosen:
        o = {k: r.get(k,"") for k in HEADER}
        # ensure types/strings
        o["rank"] = str(o.get("rank","")).strip() or "1"
        o["approve"] = "y"
        o["is_human"] = "True"
        out.append(o)
    return out

def main():
    if not APP.exists():
        print(f"ERROR: {APP} not found", file=sys.stderr)
        sys.exit(1)

    # backup
    bkp = BACKUPS / f"wikidata_approved.csv.bak"
    shutil.copy2(APP, bkp)
    print(f"Backup written → {bkp}")

    rows = load_rows(APP)
    cleaned = sanitize(rows)
    write_rows(APP, cleaned)
    print(f"Sanitized {len(rows)} → {len(cleaned)} rows (1 per author).")
    # quick spot checks
    for aid in ("grey-alex","baring-anne","berry-thomas","clark-w-c","aurobindo-sri","mcdermott-robert"):
        hits = [r for r in cleaned if r["author_id"] == aid]
        if hits:
            print(f" {aid:>18}: {hits[0]['chosen_qid']}  {hits[0]['label'] or ''}")

if __name__ == "__main__":
    main()
