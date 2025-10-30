# tools/orcid_seed_strict.py
#!/usr/bin/env python3
"""
ORCID Seed (Strict) — auto-approve high-confidence ORCID matches

What this does
--------------
Reads an ORCID candidate list (typically produced by tools/orcid_candidates.py),
applies conservative heuristics (surname match, fuzzy name score, rank filter,
pre-1900 guard, etc.), and writes a vetted approvals CSV that downstream tools
can apply to authors.master.yaml.

Inputs (files)
--------------
- ORCID_REVIEW (env, optional)  → defaults to: citations/_manifests/orcid_review.csv
- AUTH_MASTER  (env, optional)  → defaults to: citations/authors.master.yaml
  Used to parse lifespans so we avoid assigning ORCIDs to historical figures.

Outputs (files)
---------------
- ORCID_APPROVED (env, optional) → defaults to: citations/_manifests/orcid_approved.csv

Safety heuristics (default)
---------------------------
- Consider only top rank 1–2 candidates.
- Require surname token match (handles “St John” style surnames).
- Require fuzzy token-sort ratio ≥ 92 unless given-name initial also matches.
- If a birth year is present in master and < 1900, skip (ORCID is modern).
- One approval per author_id (first passing candidate wins).

Usage
-----
python3 tools/orcid_seed_strict.py
# optional environment overrides:
#   AUTH_MASTER=citations/authors.master.FOCUS.yaml \
#   ORCID_REVIEW=citations/_manifests/orcid_review.csv \
#   ORCID_APPROVED=citations/_manifests/orcid_approved.csv \
#   python3 tools/orcid_seed_strict.py

Notes
-----
- Requires: pip install rapidfuzz pyyaml
- Idempotent: re-running will rewrite the approved CSV deterministically.
"""

import os, csv, re, unicodedata, pathlib, sys
from typing import Optional

try:
    from rapidfuzz import fuzz
except ImportError:
    print("Missing rapidfuzz. Install with: pip install rapidfuzz", file=sys.stderr); sys.exit(2)

try:
    import yaml
except ImportError:
    print("Missing pyyaml. Install with: pip install pyyaml", file=sys.stderr); sys.exit(2)

# Inputs/outputs (allow override)
IN  = pathlib.Path(os.environ.get("ORCID_REVIEW",  "citations/_manifests/orcid_review.csv"))
OUT = pathlib.Path(os.environ.get("ORCID_APPROVED","citations/_manifests/orcid_approved.csv"))
AUTH_MASTER = pathlib.Path(os.environ.get("AUTH_MASTER", "citations/authors.master.yaml"))

ORCID_RE = re.compile(r'(?:https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$')
EN_DASH_HYPHEN = r'[\u2013-]'

def ascii_fold(s: str) -> str:
    return unicodedata.normalize('NFKD', (s or '')).encode('ascii','ignore').decode().strip()

def norm(s: str) -> str:
    return " ".join(ascii_fold(s).lower().split())

def bare_orcid(s: str) -> Optional[str]:
    m = ORCID_RE.search((s or "").strip())
    return m.group(1) if m else None

def split_author_id(aid: str):
    """
    id format: family-given[-middle...]
    returns: (family_token, given_initial) both normalized
    """
    parts = (aid or '').split('-')
    family = parts[0] if parts else ''
    given  = parts[1] if len(parts) > 1 else ''
    return norm(family), (norm(given)[:1] if given else '')

def last_token(s: str) -> str:
    toks = norm(s).split()
    return toks[-1] if toks else ''

def parse_birth_year(lifespan: Optional[str]) -> Optional[int]:
    if not lifespan:
        return None
    m = re.match(rf'^\s*(\d{{3,4}})\s*{EN_DASH_HYPHEN}', lifespan)
    return int(m.group(1)) if m else None

def load_birth_years() -> dict:
    """Return {author_id: birth_year or None}. If master missing/invalid, return {}."""
    if not AUTH_MASTER.exists():
        return {}
    try:
        data = yaml.safe_load(AUTH_MASTER.read_text()) or {}
        out = {}
        for a in (data.get("authors") or []):
            out[a.get("id")] = parse_birth_year(a.get("lifespan"))
        return out
    except Exception:
        return {}

def ok_family_match(fullname: str, family_token: str) -> bool:
    """
    Require surname token to appear; allow multi-token surnames via token presence.
    Exact last-token match passes fast; otherwise fallback to token presence.
    """
    fn = norm(fullname)
    fam = norm(family_token)
    if not fam:
        return False
    if last_token(fn) == fam:
        return True
    return fam in fn.split()

def main():
    if not IN.exists():
        print(f"ERROR: not found {IN}", file=sys.stderr); return 2

    rows = list(csv.DictReader(IN.open()))
    out_cols = [
        "author_id","full_name","approve","chosen_orcid","note",
        "candidate_source","display_name","rank","match_score_hint","works_count","institution"
    ]

    birth_years = load_birth_years()
    if AUTH_MASTER.exists():
        print(f"📘 Using author master for safety checks: {AUTH_MASTER}")

    approved, seen = [], set()
    scanned = kept = skipped = 0

    print(f"🔎 Seeding ORCID approvals from {IN}")

    for r in rows:
        scanned += 1

        # Conservative rank filter
        if r.get("rank") not in ("1","2"):
            skipped += 1
            continue

        orcid = bare_orcid(r.get("orcid",""))
        if not orcid:
            skipped += 1
            continue

        aid  = (r.get("author_id") or "").strip()
        full = (r.get("full_name") or "").strip()
        disp = (r.get("display_name") or "").strip()

        fam, ginit = split_author_id(aid)
        if not fam or not full:
            skipped += 1
            continue

        # Historical guard: avoid asserting ORCIDs for pre-1900 births
        by = birth_years.get(aid)
        if by is not None and by < 1900:
            skipped += 1
            continue

        # Surname check
        if not ok_family_match(disp or full, fam):
            skipped += 1
            continue

        # Fuzzy similarity (robust to order/extra tokens)
        name_score = fuzz.token_sort_ratio(norm(full), norm(disp or full))

        # Given initial must match if present; else require high fuzzy score
        given_ok = bool(ginit) and norm(disp or full).startswith(ginit)
        if not (given_ok or name_score >= 92):
            skipped += 1
            continue

        # One approval per author_id; keep first/top by rank
        if aid in seen:
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
        w = csv.DictWriter(f, fieldnames=out_cols)
        w.writeheader(); w.writerows(approved)

    print(f"✅ Seeded {kept} approvals → {OUT}  (scanned={scanned}, skipped={skipped})")
    return 0

if __name__ == "__main__":
    sys.exit(main())