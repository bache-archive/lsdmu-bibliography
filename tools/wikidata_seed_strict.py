# tools/wikidata_seed_strict.py  (drop-in replacement)
#!/usr/bin/env python3
"""
Strict auto-approvals for Wikidata candidates → citations/_manifests/wikidata_approved.csv

Acceptance criteria (all must pass):
  1) Candidate is instance of human (is_human == True in review CSV)
  2) Family/surname tokens from authors.master.yaml appear at the END of the chosen label tokens
  3) Fuzzy name score ≥ 92 comparing master full_name to candidate label/aliases (diacritics folded)
  4) If master birth year is known, |birth_wd - birth_master| ≤ 2

Tie-breaks when multiple rows match for the same author_id:
  - Higher fuzzy score wins
  - If tied, lower rank wins (rank "1" preferred)
  - If still tied, prefer a row that has both birth_year and death_year present

Environment overrides:
  AUTH_MASTER: path to authors.master.yaml (default: citations/authors.master.yaml)
  IN_REVIEW:   path to wikidata_review.csv     (default: citations/_manifests/wikidata_review.csv)
  OUT_APPROVED:path to wikidata_approved.csv   (default: citations/_manifests/wikidata_approved.csv)

Requires:
  pip install rapidfuzz pyyaml
"""
from __future__ import annotations
import os, csv, pathlib, re, unicodedata, sys, shutil
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz
import yaml

AUTH_MASTER  = pathlib.Path(os.environ.get("AUTH_MASTER",  "citations/authors.master.yaml"))
IN_REVIEW    = pathlib.Path(os.environ.get("IN_REVIEW",    "citations/_manifests/wikidata_review.csv"))
OUT_APPROVED = pathlib.Path(os.environ.get("OUT_APPROVED", "citations/_manifests/wikidata_approved.csv"))
OUT_APPROVED.parent.mkdir(parents=True, exist_ok=True)

FUZZ_MIN = 92

EN_DASH_OR_HYPHEN = r'[\u2013-]'

def asciifold(s: str) -> str:
    return unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode()

def norm(s: str) -> str:
    return " ".join(asciifold(s).lower().split())

def tokens(s: str) -> List[str]:
    return norm(s).split()

def endswith_tokens(name: str, tail: List[str]) -> bool:
    nt = tokens(name)
    return len(nt) >= len(tail) and nt[-len(tail):] == tail

def birth_from_lifespan(ls: Optional[str]) -> Optional[int]:
    if not ls:
        return None
    m = re.match(rf'^\s*(\d{{3,4}})\s*{EN_DASH_OR_HYPHEN}', ls)
    return int(m.group(1)) if m else None

def parse_int(s: Optional[str]) -> Optional[int]:
    if s is None: return None
    s = str(s).strip()
    return int(s) if s.isdigit() else None

def load_authors() -> Dict[str, dict]:
    if not AUTH_MASTER.exists():
        print(f"ERROR: missing {AUTH_MASTER}", file=sys.stderr)
        sys.exit(2)
    d = yaml.safe_load(AUTH_MASTER.read_text()) or {}
    return {a["id"]: a for a in d.get("authors", [])}

def best_label_score(full_name: str, label: str, aliases: str) -> Tuple[int, str]:
    """
    Compute the best fuzzy score across label and any pipe/comma/semicolon separated aliases.
    Returns (score, chosen_label_for_note)
    """
    best = (fuzz.token_set_ratio(norm(full_name), norm(label or "")), label or "")
    if aliases:
        # aliases column may be bracketed list or delimited text; just split on common delimiters
        raw = aliases.strip().strip("[]")
        for part in re.split(r"[|,;]", raw):
            p = part.strip().strip("'\"")
            if not p:
                continue
            sc = fuzz.token_set_ratio(norm(full_name), norm(p))
            if sc > best[0]:
                best = (sc, p)
    return best

def choose_best(existing: dict | None, candidate: dict) -> dict:
    """Tie-break: higher score, then lower rank, then presence of birth/death years."""
    if not existing:
        return candidate
    a, b = existing, candidate
    # higher score wins
    if b["score"] != a["score"]:
        return b if b["score"] > a["score"] else a
    # lower rank wins (treat non-digits as large)
    ra = parse_int(a.get("rank")) or 9999
    rb = parse_int(b.get("rank")) or 9999
    if rb != ra:
        return b if rb < ra else a
    # prefer one with both birth and death filled, then birth filled
    def fullness(x):
        by = parse_int(x.get("birth_year"))
        dy = parse_int(x.get("death_year"))
        return (1 if (by and dy) else 0, 1 if by else 0)
    if fullness(b) != fullness(a):
        return b if fullness(b) > fullness(a) else a
    return a  # stable

def main():
    authors = load_authors()
    if not IN_REVIEW.exists():
        print(f"ERROR: missing {IN_REVIEW}", file=sys.stderr)
        sys.exit(2)

    rows = list(csv.DictReader(IN_REVIEW.open()))
    chosen: Dict[str, dict] = {}  # author_id -> approved row

    for r in rows:
        aid = r.get("author_id") or ""
        if not aid or aid not in authors:
            continue
        a = authors[aid]
        full = a.get("full_name") or r.get("full_name") or ""
        fam_tokens = tokens(a.get("family") or "")
        if not fam_tokens:
            # If 'family' missing in master, derive from id prefix
            fam_tokens = tokens((aid.split("-")[0]) if "-" in aid else aid)

        # must be human
        if str(r.get("is_human", "")).lower() not in ("true", "1", "yes"):
            continue

        label = r.get("label") or ""
        aliases = r.get("aliases") or ""
        if not label:
            continue

        # surname must end the label
        if not endswith_tokens(label, fam_tokens):
            continue

        # fuzzy score vs label/aliases
        score, scored_on = best_label_score(full, label, aliases)
        if score < FUZZ_MIN:
            continue

        # lifespan compatibility
        master_birth = birth_from_lifespan(a.get("lifespan"))
        cand_birth = parse_int(r.get("birth_year"))
        if master_birth is not None and cand_birth is not None and abs(master_birth - cand_birth) > 2:
            continue

        candidate = {
            "author_id": aid,
            "full_name": full,
            "approve": "y",
            "chosen_qid": r.get("candidate_qid"),
            "note": f"auto score={score} on='{scored_on}'",
            "label": label,
            "rank": r.get("rank"),
            "birth_year": r.get("birth_year"),
            "death_year": r.get("death_year"),
            "is_human": r.get("is_human"),
            "score": score,  # for tie-break only (removed on write)
        }
        chosen[aid] = choose_best(chosen.get(aid), candidate)

    # Write output (strip internal 'score' field)
    out_rows = []
    for aid, rec in chosen.items():
        rec = dict(rec)
        rec.pop("score", None)
        out_rows.append(rec)

    # Optional safety: back up existing approvals
    if OUT_APPROVED.exists():
        backup = OUT_APPROVED.with_suffix(".csv.bak")
        try:
            shutil.copy2(OUT_APPROVED, backup)
            print(f"Backup written → {backup}")
        except Exception as e:
            print(f"Warning: could not write backup: {e}", file=sys.stderr)

    with OUT_APPROVED.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "author_id","full_name","approve","chosen_qid","note","label","rank","birth_year","death_year","is_human"
        ])
        w.writeheader()
        w.writerows(sorted(out_rows, key=lambda x: x["author_id"]))

    print(f"✅ Seeded {len(out_rows)} approvals → {OUT_APPROVED}")

if __name__ == "__main__":
    sys.exit(main())