#!/usr/bin/env python3
"""
Wikidata lookup for authors missing Wikidata IDs (generous search).

What it does
------------
- Loads authors from AUTH_MASTER (default: citations/authors.master.yaml)
- Filters to those with wikidata == null
- For each author, searches Wikidata using multiple queries:
    * full_name
    * alias variants (if present)
    * context-boosted queries (per-id hints below)
- For every wbsearchentities hit, fetches entity summary (P31=human?, P569/P570 years, ORCID P496)
- Ranks hits per author; writes two files:
    1) citations/_manifests/wikidata_missing_candidates.csv  (all hits)
    2) citations/_manifests/wikidata_missing_review.csv      (top 6 per author, easy to scan)

How to run
----------
export AUTH_MASTER=citations/authors.master.yaml   # or your FOCUS file
python3 tools/wikidata_lookup_missing.py

Then open the review file, pick the right QID(s), and either:
- copy QIDs into authors.master.yaml manually, or
- add rows with approve=y and chosen_qid=<QID> to wikidata_approved.csv and run wikidata_apply.py

Notes
-----
- No external deps beyond requests+pyyaml.
- Generous scoring via difflib; you can tighten/loosen thresholds if desired.
"""

import os, csv, json, time, pathlib, re, sys, unicodedata, difflib
from typing import Dict, List, Optional
import requests
import yaml

AUTH_MASTER = pathlib.Path(os.environ.get("AUTH_MASTER", "citations/authors.master.yaml"))

OUT_CAND   = pathlib.Path("citations/_manifests/wikidata_missing_candidates.csv")
OUT_REVIEW = pathlib.Path("citations/_manifests/wikidata_missing_review.csv")
CACHE      = pathlib.Path("citations/_cache/wikidata_http.jsonl")
for p in (OUT_CAND.parent, OUT_REVIEW.parent, CACHE.parent): p.mkdir(parents=True, exist_ok=True)

UA = {
    "User-Agent": "lsdmu-bibliography/1.0 (Wikidata generous lookup; contact: bibliography-team)",
    "Accept": "application/json",
}
WD_SEARCH = "https://www.wikidata.org/w/api.php"
WD_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

def norm(s: str) -> str:
    return " ".join(unicodedata.normalize('NFKD', (s or "")).encode('ascii','ignore').decode().lower().split())

def sim(a: str, b: str) -> float:
    # quick fuzzy-ish score (0..100)
    return 100.0 * difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()

def http_get(url: str, params: dict=None, sleep=0.45, retries=3):
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
            time.sleep(0.8*attempt)
    raise last_err

def wd_search(name: str, limit=12) -> List[Dict]:
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

TIME_RE = re.compile(r'^[+\-]?(\d{3,4})-')

def parse_year(claim: dict) -> Optional[int]:
    try:
        v = claim["mainsnak"]["datavalue"]["value"]["time"]
        m = TIME_RE.match(v)
        return int(m.group(1)) if m else None
    except Exception:
        return None

def entity_summary(qid: str) -> Dict:
    data = http_get(WD_ENTITY.format(qid=qid))
    ent = (data.get("entities") or {}).get(qid, {})
    claims = ent.get("claims", {})
    p31 = []
    for c in claims.get("P31", []):
        try:
            p31.append(c["mainsnak"]["datavalue"]["value"]["id"])
        except Exception:
            pass
    birth = None
    for c in claims.get("P569", []):
        y = parse_year(c)
        if y: birth = y; break
    death = None
    for c in claims.get("P570", []):
        y = parse_year(c)
        if y: death = y; break
    orcid = None
    for c in claims.get("P496", []):
        try:
            v = c["mainsnak"]["datavalue"]["value"]
            if re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$', v):
                orcid = v; break
        except Exception:
            pass
    return {
        "is_human": "Q5" in p31,
        "birth_year": birth,
        "death_year": death,
        "orcid_on_wd": orcid or "",
    }

# Context hints to improve disambiguation (add freely)
CONTEXT = {
    "chwelos-n":            ["psychiatry", "LSD", "psychedelic"],
    "kaelen-mendel":        ["music therapy", "psychedelic", "Imperial College"],
    "bolstridge-mark":      ["psychiatry", "psilocybin", "Imperial College"],
    "fiore-edith":          ["hypnosis", "past-life", "psychology"],
    "havens-joseph":        ["psychology", "therapy", "group therapy"],
    "leininger-bruce":      ["reincarnation", "Soul Survivor", "James Leininger"],
    "leininger-andrea":     ["reincarnation", "Soul Survivor", "James Leininger"],
    "lucas-winafred":       ["hypnotherapy", "past-life", "psychology"],
    "netherton-morris":     ["past-life therapy", "psychology", "hypnosis"],
    "oroc-james":           ["psychedelics", "5-MeO-DMT", "Tryptamine Palace"],
    "valarino-evelyn":      ["near-death", "NDE", "Kenneth Ring"],
    "zinser-thomas":        ["psychologist", "Soul-Centered Healing", "hypnosis"],
}

def main():
    print(f"📘 Using author master: {AUTH_MASTER}")
    master = yaml.safe_load(AUTH_MASTER.read_text())
    missing = [a for a in master["authors"] if not a.get("wikidata")]

    # only the 12 you listed, but script will work for any missing set
    rows = []
    for a in missing:
        aid = a["id"]
        full = a["full_name"]
        alias_vars = []
        try:
            alias_vars = (a.get("aliases") or {}).get("variants") or []
        except Exception:
            pass

        queries = [full]
        queries += alias_vars
        for kw in CONTEXT.get(aid, []):
            queries.append(f"{full} {kw}")

        seen_q = set()
        for q in queries:
            hits = wd_search(q, limit=12)
            for rank, h in enumerate(hits, 1):
                qid = h.get("id")
                if not qid or qid in seen_q:
                    continue
                seen_q.add(qid)
                meta = entity_summary(qid)
                score = max(sim(full, h.get("label") or ""),
                            *(sim(full, al) for al in (h.get("aliases") or []) or [0]))

                rows.append({
                    "author_id": aid,
                    "full_name": full,
                    "query_used": q,
                    "rank": rank,
                    "candidate_qid": qid,
                    "label": h.get("label") or "",
                    "description": h.get("description") or "",
                    "aliases": "|".join(h.get("aliases") or []),
                    "is_human": meta["is_human"],
                    "birth_year": meta["birth_year"] or "",
                    "death_year": meta["death_year"] or "",
                    "orcid_on_wd": meta["orcid_on_wd"],
                    "name_similarity": f"{score:.1f}",
                })

    # write all candidates
    with OUT_CAND.open("w", newline="") as f:
        cols = ["author_id","full_name","query_used","rank","candidate_qid","label","description",
                "aliases","is_human","birth_year","death_year","orcid_on_wd","name_similarity"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)

    # top-N review per author
    per = {}
    for r in rows:
        per.setdefault(r["author_id"], []).append(r)
    review = []
    for aid, lst in per.items():
        # sort: is_human desc, name_similarity desc, has birth_year desc, rank asc
        def key(x):
            return (
                0 if x["is_human"] else 1,
                -float(x["name_similarity"] or 0),
                0 if str(x["birth_year"]).strip() else 1,
                int(x["rank"] or 99999),
            )
        lst.sort(key=key)
        review.extend(lst[:6])

    with OUT_REVIEW.open("w", newline="") as f:
        cols = ["author_id","full_name","candidate_qid","label","description",
                "birth_year","death_year","is_human","name_similarity","query_used","aliases","orcid_on_wd","rank"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(review)

    print(f"✳️ wrote {OUT_CAND}")
    print(f"✳️ wrote {OUT_REVIEW}")
    print("👉 Open the review CSV, pick QIDs, then apply via wikidata_apply.py or manual edit to master.")

if __name__ == "__main__":
    main()