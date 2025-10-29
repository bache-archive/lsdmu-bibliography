# tools/orcid_seed_strict.py
#!/usr/bin/env python3
import csv, re, unicodedata, pathlib, sys
try:
    from rapidfuzz import fuzz
except ImportError:
    print("Missing rapidfuzz. Install with: pip install rapidfuzz", file=sys.stderr); sys.exit(2)

IN = pathlib.Path("citations/_manifests/orcid_review.csv")
OUT = pathlib.Path("citations/_manifests/orcid_approved.csv")

ORCID_RE = re.compile(r'(?:https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$')

def ascii_fold(s: str) -> str:
    return unicodedata.normalize('NFKD', (s or '')).encode('ascii','ignore').decode().strip()

def norm(s: str) -> str:
    return " ".join(ascii_fold(s).lower().split())

def bare_orcid(s: str) -> str|None:
    m = ORCID_RE.search((s or "").strip())
    return m.group(1) if m else None

def split_author_id(aid: str):
    # id = family-given[-middle...]; we want family and first given token
    parts = (aid or '').split('-')
    family = parts[0] if parts else ''
    given = parts[1] if len(parts) > 1 else ''
    return norm(family), norm(given)[:1]  # family, given initial

def ok_family_match(fullname: str, family_token: str) -> bool:
    # require family token to appear as a whole-token at end OR anywhere as a token
    toks = norm(fullname).split()
    return (toks and toks[-1] == family_token) or (family_token in toks)

def main():
    if not IN.exists():
        print(f"ERROR: not found {IN}", file=sys.stderr); return 2

    rows = list(csv.DictReader(IN.open()))
    out_cols = ["author_id","full_name","approve","chosen_orcid","note",
                "candidate_source","display_name","rank","match_score_hint","works_count","institution"]

    approved = []
    seen = set()
    kept, scanned = 0, 0

    for r in rows:
        scanned += 1

        # limit to top ranks for safety (tweakable)
        if r.get("rank") not in ("1","2"):
            continue

        orcid = bare_orcid(r.get("orcid",""))
        if not orcid:
            continue

        aid = r.get("author_id","").strip()
        full = r.get("full_name","").strip()
        disp = r.get("display_name","").strip()

        fam, ginit = split_author_id(aid)
        if not fam or not full:
            continue

        # require family token match
        if not ok_family_match(disp or full, fam):
            continue

        # fuzzy name similarity (token sort ratio is robust to order/extra tokens)
        name_score = fuzz.token_sort_ratio(norm(full), norm(disp or full))

        # accept: strong fuzzy OR given-initial confirmation
        given_ok = bool(ginit) and norm(disp or full)[:1] == ginit
        if name_score < 92 and not given_ok:
            continue

        if aid in seen:
            # keep only the higher score (or rank 1 over 2)
            continue
        seen.add(aid)

        approved.append({
            "author_id": aid,
            "full_name": full,
            "approve": "y",
            "chosen_orcid": orcid,
            "note": f"score={name_score}" + (", given-initial" if given_ok else ""),
            "candidate_source": r.get("candidate_source"),
            "display_name": r.get("display_name"),
            "rank": r.get("rank"),
            "match_score_hint": r.get("match_score_hint"),
            "works_count": r.get("works_count"),
            "institution": r.get("institution"),
        })
        kept += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_cols); w.writeheader(); w.writerows(approved)

    print(f"Seeded {kept} approvals → {OUT}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
