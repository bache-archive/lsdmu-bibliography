# tools/wikidata_candidates.py
#!/usr/bin/env python3
"""
Generate Wikidata candidate rows for each author in citations/authors.master.yaml.

Outputs:
  - citations/_manifests/wikidata_candidates.csv  (raw candidates, many per author)
  - citations/_manifests/wikidata_review.csv      (ranked, first N per author)
Caches:
  - citations/_cache/wikidata_http.jsonl

Run:
  python3 tools/wikidata_candidates.py
"""
import csv, json, time, pathlib, re, sys, unicodedata
from typing import Dict, List, Optional
import requests
import yaml

AUTH_MASTER = pathlib.Path("citations/authors.master.yaml")
OUT_CAND = pathlib.Path("citations/_manifests/wikidata_candidates.csv")
OUT_REVIEW = pathlib.Path("citations/_manifests/wikidata_review.csv")
CACHE = pathlib.Path("citations/_cache/wikidata_http.jsonl")
CACHE.parent.mkdir(parents=True, exist_ok=True)
OUT_CAND.parent.mkdir(parents=True, exist_ok=True)

UA = {
    "User-Agent": "lsdmu-bibliography/1.0 (Wikidata discovery; contact: bibliography-team)",
    "Accept": "application/json",
}
WD_SEARCH = "https://www.wikidata.org/w/api.php"
WD_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

def norm(s: str) -> str:
    return " ".join(unicodedata.normalize('NFKD', (s or "")).encode('ascii','ignore').decode().lower().split())

def http_get(url: str, params: dict=None, sleep=0.4, retries=3):
    key = {"url": url, "params": params or {}}
    kstr = json.dumps(key, sort_keys=True)
    if CACHE.exists():
        with CACHE.open() as f:
            for line in f:
                rec = json.loads(line)
                if rec["key"] == kstr:
                    return rec["data"]
    last_err = None
    for attempt in range(1, retries+1):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 429:
                time.sleep(1.2*attempt); continue
            r.raise_for_status()
            data = r.json()
            with CACHE.open("a") as f:
                f.write(json.dumps({"key": kstr, "data": data}) + "\n")
            time.sleep(sleep)
            return data
        except Exception as e:
            last_err = e
            time.sleep(0.6*attempt)
    raise last_err

def wd_search_person(name: str, limit=8) -> List[Dict]:
    """Search Wikidata for label matches; return lightweight results."""
    params = {
        "action":"wbsearchentities",
        "format":"json",
        "language":"en",
        "uselang":"en",
        "type":"item",
        "search": name,
        "limit": limit,
    }
    data = http_get(WD_SEARCH, params=params)
    out = []
    for r in data.get("search", []):
        out.append({
            "id": r.get("id"),
            "label": r.get("label"),
            "description": r.get("description"),
            "aliases": r.get("aliases") or [],
        })
    return out

def parse_time_value(claim: dict) -> Optional[int]:
    """
    Extract year from a Wikidata time claim snak value like '+1872-08-15T00:00:00Z'.
    """
    try:
        v = claim["mainsnak"]["datavalue"]["value"]["time"]
        m = re.match(r'^[+\-]?(\d{3,4})-', v)
        return int(m.group(1)) if m else None
    except Exception:
        return None

def wd_entity_summary(qid: str) -> Dict:
    data = http_get(WD_ENTITY.format(qid=qid))
    ent = (data.get("entities") or {}).get(qid, {})
    claims = ent.get("claims", {})
    # instance of (P31), human is Q5
    p31 = [c["mainsnak"]["datavalue"]["value"]["id"] for c in claims.get("P31", []) if "datavalue" in c.get("mainsnak", {})]
    # birth (P569), death (P570)
    birth = None
    for c in claims.get("P569", []):
        y = parse_time_value(c)
        if y: birth = y; break
    death = None
    for c in claims.get("P570", []):
        y = parse_time_value(c)
        if y: death = y; break
    # ORCID (P496) if present
    orcid = None
    for c in claims.get("P496", []):
        try:
            v = c["mainsnak"]["datavalue"]["value"]
            if re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$', v):
                orcid = v; break
        except Exception:
            pass
    # nationality (P27) labels are not in this endpoint directly; skip for now
    return {"p31": p31, "birth_year": birth, "death_year": death, "orcid": orcid}

def birth_from_lifespan(ls: Optional[str]) -> Optional[int]:
    if not ls: return None
    m = re.match(r'^\s*(\d{3,4})\s*[\u2013-]', ls)
    return int(m.group(1)) if m else None

def main():
    master = yaml.safe_load(AUTH_MASTER.read_text())
    authors = [a for a in master["authors"] if a.get("entity_type") == "person"]

    rows = []
    for i, a in enumerate(authors, 1):
        full = a["full_name"]
        aid = a["id"]
        print(f"[{i}/{len(authors)}] search:", full)
        hits = wd_search_person(full, limit=10)
        for rank, h in enumerate(hits, 1):
            qid = h.get("id")
            meta = wd_entity_summary(qid) if qid else {}
            rows.append({
                "author_id": aid,
                "full_name": full,
                "rank": rank,
                "candidate_qid": qid,
                "label": h.get("label"),
                "description": h.get("description"),
                "aliases": "|".join(h.get("aliases") or []),
                "is_human": "Q5" in (meta.get("p31") or []),
                "birth_year": meta.get("birth_year"),
                "death_year": meta.get("death_year"),
                "orcid_on_wd": meta.get("orcid") or "",
            })

    with OUT_CAND.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "author_id","full_name","rank","candidate_qid","label","description","aliases",
            "is_human","birth_year","death_year","orcid_on_wd"
        ])
        w.writeheader(); w.writerows(rows)

    # Also produce a smaller review file with top-5 per author
    small = []
    by = {}
    for r in rows:
        by.setdefault(r["author_id"], []).append(r)
    for aid, lst in by.items():
        lst = sorted(lst, key=lambda x: x["rank"])[:5]
        small.extend(lst)
    with OUT_REVIEW.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "author_id","full_name","rank","candidate_qid","label","description","aliases",
            "is_human","birth_year","death_year","orcid_on_wd"
        ])
        w.writeheader(); w.writerows(small)

    print(f"✳️ wrote {OUT_CAND} and {OUT_REVIEW}")

if __name__ == "__main__":
    main()
