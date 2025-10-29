# tools/wikidata_seed_strict.py
#!/usr/bin/env python3
"""
Strict auto-approvals for Wikidata candidates → citations/_manifests/wikidata_approved.csv

Logic:
 - fuzzy name score ≥ 92 (normalized)
 - surname tokens (from authors.master.yaml 'family') must match the END of label
 - instance of human (Q5)
 - lifespan compatibility: if master birth year exists, |birth_wd - birth_master| ≤ 2

Run:
  pip install rapidfuzz pyyaml
  python3 tools/wikidata_seed_strict.py
"""
import csv, pathlib, re, unicodedata, yaml
from rapidfuzz import fuzz

AUTH_MASTER = pathlib.Path("citations/authors.master.yaml")
IN_REVIEW = pathlib.Path("citations/_manifests/wikidata_review.csv")
OUT_APPROVED = pathlib.Path("citations/_manifests/wikidata_approved.csv")
OUT_APPROVED.parent.mkdir(parents=True, exist_ok=True)

def norm(s: str) -> str:
    return " ".join(unicodedata.normalize('NFKD', (s or "")).encode('ascii','ignore').decode().lower().split())

def tokens(s: str): return norm(s).split()

def endswith_tokens(name: str, tail: list[str]) -> bool:
    nt = tokens(name)
    return len(nt) >= len(tail) and nt[-len(tail):] == tail

def birth_from_lifespan(ls: str):
    if not ls: return None
    m = re.match(r'^\s*(\d{3,4})\s*[\u2013-]', ls)
    return int(m.group(1)) if m else None

def load_authors():
    d = yaml.safe_load(AUTH_MASTER.read_text())
    by_id = {a["id"]: a for a in d["authors"]}
    return by_id

def main():
    auth = load_authors()
    rows = list(csv.DictReader(IN_REVIEW.open()))
    approvals = []
    for r in rows:
        aid = r["author_id"]
        a = auth.get(aid, {})
        full = a.get("full_name") or r["full_name"]
        fam = tokens(a.get("family",""))
        label = r.get("label") or ""
        if not fam or not label:
            continue
        # must be human
        if str(r.get("is_human")).lower() not in ("true","1","yes"):
            continue
        # surname must end the label tokens
        if not endswith_tokens(label, fam):
            continue
        # fuzzy match on full name vs label
        score = fuzz.token_set_ratio(norm(full), norm(label))
        if score < 92:
            continue
        # lifespan compatibility (if known)
        master_birth = birth_from_lifespan(a.get("lifespan") or "")
        cand_birth = int(r["birth_year"]) if (r.get("birth_year") or "").isdigit() else None
        if master_birth and cand_birth and abs(master_birth - cand_birth) > 2:
            continue

        approvals.append({
            "author_id": aid,
            "full_name": full,
            "approve": "y",
            "chosen_qid": r["candidate_qid"],
            "note": f"auto score={score}",
            "label": r["label"],
            "rank": r["rank"],
            "birth_year": r["birth_year"],
            "death_year": r["death_year"],
            "is_human": r["is_human"],
        })

    with OUT_APPROVED.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "author_id","full_name","approve","chosen_qid","note","label","rank","birth_year","death_year","is_human"
        ])
        w.writeheader(); w.writerows(approvals)

    print(f"✅ Seeded {len(approvals)} approvals → {OUT_APPROVED}")

if __name__ == "__main__":
    main()
