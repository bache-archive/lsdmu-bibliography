# tools/wikidata_candidates.py
#!/usr/bin/env python3
"""
Generate Wikidata candidate rows for each author in citations/authors.master.yaml.

Outputs:
  - citations/_manifests/wikidata_candidates.csv  (raw candidates, many per author)
  - citations/_manifests/wikidata_review.csv      (ranked, first N per author)
Caches:
  - citations/_cache/wikidata_http.jsonl

Usage:
  AUTH_MASTER=citations/authors.master.FOCUS.yaml python3 tools/wikidata_candidates.py
  # or just:
  python3 tools/wikidata_candidates.py
"""

from __future__ import annotations
import os, csv, json, time, pathlib, re, sys, unicodedata
from typing import Dict, List, Optional, Any
import requests
import yaml

# ---------- Config & Paths ----------
AUTH_MASTER_PATH = os.environ.get("AUTH_MASTER", "citations/authors.master.yaml")
AUTH_MASTER = pathlib.Path(AUTH_MASTER_PATH)

OUT_CAND   = pathlib.Path("citations/_manifests/wikidata_candidates.csv")
OUT_REVIEW = pathlib.Path("citations/_manifests/wikidata_review.csv")
CACHE      = pathlib.Path("citations/_cache/wikidata_http.jsonl")

CACHE.parent.mkdir(parents=True, exist_ok=True)
OUT_CAND.parent.mkdir(parents=True, exist_ok=True)

print(f"📘 Using author master: {AUTH_MASTER}")

UA = {
    "User-Agent": "lsdmu-bibliography/1.0 (Wikidata discovery; contact: bibliography-team)",
    "Accept": "application/json",
}
WD_SEARCH = "https://www.wikidata.org/w/api.php"
WD_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

# ---------- Helpers ----------
def norm(s: str) -> str:
    return " ".join(
        unicodedata.normalize('NFKD', (s or "")).encode('ascii','ignore').decode().lower().split()
    )

def tokens(s: str) -> List[str]:
    return norm(s).split()

def family_tail_match(label: str, family: str) -> bool:
    """True if the label ends with the family token as a whole word."""
    if not family or not label:
        return False
    ltoks = tokens(label)
    return bool(ltoks) and ltoks[-1] == norm(family)

def json_or_text(r: requests.Response) -> Any:
    """Parse JSON when possible even if Content-Type is wrong; otherwise return {'_raw': text}."""
    ctype = (r.headers.get("Content-Type") or "").lower()
    if "json" in ctype:
        return r.json()
    try:
        return r.json()
    except Exception:
        return {"_raw": r.text}

def http_get(url: str, params: dict | None = None, sleep=0.35, retries=3):
    """GET with tiny line-cache, polite UA, and retry/backoff."""
    key = {"url": url, "params": params or {}}
    kstr = json.dumps(key, sort_keys=True)

    # Cache lookup
    if CACHE.exists():
        with CACHE.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("key") == kstr:
                    return rec.get("data")

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 429:
                # Gentle backoff on rate-limit
                time.sleep(1.2 * attempt)
                continue
            r.raise_for_status()
            data = json_or_text(r)

            # Cache store
            with CACHE.open("a") as f:
                f.write(json.dumps({"key": kstr, "data": data}) + "\n")

            time.sleep(sleep)
            return data
        except Exception as e:
            last_err = e
            time.sleep(0.6 * attempt)

    raise last_err

def wd_search_person(name: str, limit=8) -> List[Dict]:
    """Search Wikidata label/aliases. Returns basic candidates."""
    if not name:
        return []
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": "en",
        "uselang": "en",
        "type": "item",
        "search": name,
        "limit": limit,
    }
    data = http_get(WD_SEARCH, params=params)
    out = []
    for r in (data.get("search") or []):
        out.append({
            "id": r.get("id"),
            "label": r.get("label") or "",
            "description": r.get("description") or "",
            "aliases": r.get("aliases") or [],
        })
    return out

TIME_RE = re.compile(r'^[+\-]?(\d{3,4})-')

def parse_time_value(claim: dict) -> Optional[int]:
    """Extract year from Wikidata time snak (e.g. '+1872-08-15T00:00:00Z')."""
    try:
        v = claim["mainsnak"]["datavalue"]["value"]["time"]
        m = TIME_RE.match(v)
        return int(m.group(1)) if m else None
    except Exception:
        return None

def wd_entity_summary(qid: str) -> Dict:
    """Light summary for scoring/review: P31 (human?), P569, P570, P496 (ORCID)."""
    if not qid:
        return {}
    data = http_get(WD_ENTITY.format(qid=qid))
    ent = (data.get("entities") or {}).get(qid, {})
    claims = ent.get("claims", {}) or {}

    # instance of (P31) → human Q5?
    p31 = []
    for c in claims.get("P31", []):
        try:
            p31.append(c["mainsnak"]["datavalue"]["value"]["id"])
        except Exception:
            pass

    birth = next((y for y in (parse_time_value(c) for c in claims.get("P569", [])) if y), None)
    death = next((y for y in (parse_time_value(c) for c in claims.get("P570", [])) if y), None)

    orcid = None
    for c in claims.get("P496", []):
        try:
            v = c["mainsnak"]["datavalue"]["value"]
            if re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$', v):
                orcid = v
                break
        except Exception:
            pass

    return {"p31": p31, "birth_year": birth, "death_year": death, "orcid": orcid}

def birth_from_lifespan(ls: Optional[str]) -> Optional[int]:
    if not ls: return None
    m = re.match(r'^\s*(\d{3,4})\s*[\u2013-]', ls)
    return int(m.group(1)) if m else None

# Very light token-set similarity (0..100). Keeps script stdlib-only.
def simple_name_score(a: str, b: str) -> int:
    ta = set(tokens(a))
    tb = set(tokens(b))
    if not ta or not tb:
        return 0
    overlap = len(ta & tb)
    base = 100 * overlap / max(len(ta), len(tb))
    # small bonus for exact last-token (family) match
    if tokens(a)[-1:] == tokens(b)[-1:]:
        base += 5
    return int(min(100, round(base)))

# ---------- Main ----------
def main():
    master = yaml.safe_load(AUTH_MASTER.read_text())
    authors = [a for a in master.get("authors", []) if a.get("entity_type") == "person"]

    rows: List[Dict[str, Any]] = []
    for i, a in enumerate(authors, 1):
        aid  = a.get("id")
        full = a.get("full_name") or ""
        fam  = a.get("family") or ""
        giv  = a.get("given") or ""
        print(f"[{i}/{len(authors)}] search:", full)

        # Primary search: full name
        hits = wd_search_person(full, limit=10)

        # Fallbacks if too few: family only, then family + given
        if len(hits) < 2 and fam:
            hits += wd_search_person(fam, limit=5)
        if len(hits) < 2 and fam and giv:
            hits += wd_search_person(f"{fam} {giv}", limit=5)

        # De-dupe by QID while preserving order
        seen_q = set()
        uniq_hits = []
        for h in hits:
            qid = h.get("id")
            if not qid or qid in seen_q:
                continue
            seen_q.add(qid)
            uniq_hits.append(h)

        # Build candidate rows
        for rank, h in enumerate(uniq_hits, 1):
            qid = h.get("id") or ""
            meta = wd_entity_summary(qid) if qid else {}
            label = h.get("label") or ""
            name_score = simple_name_score(full, label)
            rows.append({
                "author_id": aid,
                "full_name": full,
                "rank": rank,
                "candidate_qid": qid,
                "label": label,
                "description": h.get("description") or "",
                "aliases": "|".join([x for x in (h.get("aliases") or []) if isinstance(x, str)]),
                "is_human": "Q5" in (meta.get("p31") or []),
                "birth_year": meta.get("birth_year") or "",
                "death_year": meta.get("death_year") or "",
                "orcid_on_wd": meta.get("orcid") or "",
                # helper fields for downstream review (non-binding)
                "family_tail_match": family_tail_match(label, fam),
                "name_score_hint": name_score,
            })

    # Write full candidates
    cand_fields = [
        "author_id","full_name","rank","candidate_qid","label","description","aliases",
        "is_human","birth_year","death_year","orcid_on_wd",
        "family_tail_match","name_score_hint"
    ]
    with OUT_CAND.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cand_fields)
        w.writeheader(); w.writerows(rows)

    # Produce compact review file: top 5 per author by rank, with light re-rank by helpers
    by_author: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        by_author.setdefault(r["author_id"], []).append(r)

    review_rows: List[Dict[str, Any]] = []
    for aid, lst in by_author.items():
        def score_key(x):
            # Prefer rank, then human, then family tail match, then name_score_hint
            rank = int(x.get("rank") or 9999)
            human_bonus = 0 if str(x.get("is_human")).lower() not in ("true","1","yes") else -1
            tail_bonus  = 0 if not x.get("family_tail_match") else -1
            # negative bonus sorts earlier; finally, sort by higher name_score descending
            return (rank, human_bonus, tail_bonus, -int(x.get("name_score_hint") or 0))
        top = sorted(lst, key=score_key)[:5]
        review_rows.extend(top)

    with OUT_REVIEW.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cand_fields)
        w.writeheader(); w.writerows(review_rows)

    print(f"✳️ wrote {OUT_CAND} and {OUT_REVIEW}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)