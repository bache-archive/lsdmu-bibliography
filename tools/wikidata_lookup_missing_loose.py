#!/usr/bin/env python3
"""
wikidata_lookup_missing_loose.py
Purpose: Find Wikidata candidates for authors who currently lack a QID,
         using multiple query patterns + field-derived context tokens.

Inputs:
  AUTH_MASTER (env) → defaults to citations/authors.master.yaml
Outputs:
  citations/_manifests/wikidata_missing_candidates.csv
  citations/_manifests/wikidata_missing_review.csv

Usage:
  export AUTH_MASTER=citations/authors.master.yaml
  python3 tools/wikidata_lookup_missing_loose.py
  csvlook -I citations/_manifests/wikidata_missing_review.csv | head -n 40
Then pick QIDs and apply with: python3 tools/wikidata_apply.py citations/_manifests/wikidata_missing_review.csv
"""
import os, csv, json, time, pathlib, re, sys, unicodedata
from typing import Dict, List, Optional
import yaml
import requests

AUTH_MASTER = pathlib.Path(os.environ.get("AUTH_MASTER", "citations/authors.master.yaml"))
OUT_DIR = pathlib.Path("citations/_manifests")
OUT_CAND = OUT_DIR / "wikidata_missing_candidates.csv"
OUT_REVIEW = OUT_DIR / "wikidata_missing_review.csv"
CACHE = pathlib.Path("citations/_cache/wd_loose_http.jsonl")

for p in (OUT_DIR, CACHE.parent):
    p.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "lsdmu-bibliography/1.0 (Wikidata missing lookup; contact: bibliography-team)",
      "Accept": "application/json"}
WD_SEARCH = "https://www.wikidata.org/w/api.php"
WD_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

def norm(s:str) -> str:
    return " ".join(unicodedata.normalize('NFKD', (s or "")).encode('ascii','ignore').decode().lower().split())

def tokens(s:str) -> List[str]:
    return norm(s).split()

def http_get(url: str, params: dict=None, sleep=0.4, retries=3):
    key = {"url": url, "params": params or {}}
    kstr = json.dumps(key, sort_keys=True)
    if CACHE.exists():
        with CACHE.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec.get("key") == kstr:
                        return rec["data"]
                except: pass
    last_err = None
    for attempt in range(1, retries+1):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 429:
                time.sleep(1.0 * attempt); continue
            r.raise_for_status()
            data = r.json()
            with CACHE.open("a") as f:
                f.write(json.dumps({"key": kstr, "data": data}) + "\n")
            time.sleep(sleep)
            return data
        except Exception as e:
            last_err = e
            time.sleep(0.6 * attempt)
    raise last_err

def wd_search(name: str, limit=12) -> List[Dict]:
    params = {"action":"wbsearchentities","format":"json","language":"en","uselang":"en",
              "type":"item","search": name,"limit":limit}
    data = http_get(WD_SEARCH, params=params)
    out=[]
    for r in data.get("search", []):
        out.append({"id":r.get("id"),"label":r.get("label"),"description":r.get("description")})
    return out

YEAR = re.compile(r'^[+\-]?(\d{3,4})-')
def parse_time(claim):
    try:
        t = claim["mainsnak"]["datavalue"]["value"]["time"]
        m = YEAR.match(t)
        return int(m.group(1)) if m else None
    except Exception:
        return None

def wd_entity_summary(qid: str) -> Dict:
    data = http_get(WD_ENTITY.format(qid=qid))
    ent = (data.get("entities") or {}).get(qid, {})
    claims = ent.get("claims", {})
    p31 = []
    for c in claims.get("P31", []):
        try:
            p31.append(c["mainsnak"]["datavalue"]["value"]["id"])
        except: pass
    birth = next((y for y in (parse_time(c) for c in claims.get("P569", [])) if y), None)
    death = next((y for y in (parse_time(c) for c in claims.get("P570", [])) if y), None)
    return {"p31": p31, "birth_year": birth, "death_year": death}

def birth_from_lifespan(ls: Optional[str]) -> Optional[int]:
    if not ls: return None
    m = re.match(r'^\s*(\d{3,4})\s*[\u2013-]', ls)
    return int(m.group(1)) if m else None

# Lightweight scorer
def endswith_family(label: str, family: str) -> bool:
    lt = tokens(label)
    ft = tokens(family)
    return bool(lt) and bool(ft) and lt[-1] == ft[-1]

def score_candidate(full: str, family: str, label: str, is_human: bool,
                    birth_wd: Optional[int], birth_master: Optional[int]) -> float:
    s = 0.0
    if is_human: s += 3.0
    if endswith_family(label or "", family): s += 2.0
    # fuzzy-lite: token overlap
    fset = set(tokens(full)); lset = set(tokens(label or ""))
    s += min(3.0, len(fset & lset) * 0.7)
    if birth_wd and birth_master:
        diff = abs(birth_wd - birth_master)
        s += max(0.0, 2.0 - min(diff, 5) * 0.4)  # full 2 if same year, decays
    return s

# field → context keywords to bias searches
FIELD_HINTS = {
    "psychiatry": ["psychiatrist","psychotherapy","LSD","psychedelic"],
    "psychotherapy": ["therapist","hypnotherapist","past-life","regression"],
    "neuroscience": ["neuroscientist","UCL","Imperial College","music"],
    "art": ["artist"],
    "reincarnation": ["reincarnation","past-life"],
    "hypnosis": ["hypnosis","hypnotherapist"],
    "psychology": ["psychologist"],
    "editor": ["author","editor"],
}

def build_queries(a: Dict) -> List[str]:
    full = a["full_name"]
    fam = a.get("family") or ""
    giv = a.get("given") or ""
    qs = set()

    # base
    qs.add(full)

    # initials handling (e.g., "N. Chwelos")
    if re.match(r'^[A-Za-z]\.?$', giv.strip()) or re.match(r'^[A-Za-z]\.\s*[A-Za-z]\.?$', giv.strip()):
        qs.add(f"{fam}")  # family-only fallback
        # try some common first-name guesses for single initials
        ini = giv[0].upper() if giv else ""
        for guess in ("Nick","Nicholas","Norman","Neil","N"):  # tweakable for 'N.'
            if ini == "N":
                qs.add(f"{guess} {fam}")

    # swap order
    if fam and giv:
        qs.add(f"{giv} {fam}")

    # context tokens from fields
    for fld in (a.get("fields") or []):
        for k in FIELD_HINTS.get(fld, []):
            qs.add(f"{full} {k}")
            if fam and giv:
                qs.add(f"{giv} {fam} {k}")

    # dedupe & cap
    return list(qs)[:12]

def main():
    print(f"📘 Using author master: {AUTH_MASTER}")
    master = yaml.safe_load(AUTH_MASTER.read_text())
    missing = [a for a in master["authors"] if a.get("entity_type")=="person" and not a.get("wikidata")]

    rows=[]
    for a in missing:
        full = a["full_name"]; aid = a["id"]
        birth_m = birth_from_lifespan(a.get("lifespan"))
        fam = a.get("family") or ""
        for q in build_queries(a):
            hits = wd_search(q, limit=8)
            for rank, h in enumerate(hits, 1):
                qid = h.get("id")
                meta = wd_entity_summary(qid) if qid else {}
                is_h = "Q5" in (meta.get("p31") or [])
                sc = score_candidate(full, fam, h.get("label") or "", is_h,
                                     meta.get("birth_year"), birth_m)
                rows.append({
                    "author_id": aid,
                    "full_name": full,
                    "candidate_qid": qid,
                    "label": h.get("label"),
                    "description": h.get("description"),
                    "birth_year": meta.get("birth_year") or "",
                    "death_year": meta.get("death_year") or "",
                    "is_human": is_h,
                    "name_similarity": f"{sc:.2f}",
                    "query_used": q,
                    "rank": rank
                })

    # write big candidates
    with OUT_CAND.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["author_id","full_name","candidate_qid","label","description","birth_year","death_year","is_human","name_similarity","query_used","rank"])
        w.writeheader(); w.writerows(rows)
    print(f"✳️ wrote {OUT_CAND}")

    # write review: top 8 per author by score (desc), then by rank
    by={}
    for r in rows:
        by.setdefault(r["author_id"], []).append(r)
    review=[]
    for aid, lst in by.items():
        lst.sort(key=lambda x: (-float(x["name_similarity"]), int(x["rank"])))
        review.extend(lst[:8])
    with OUT_REVIEW.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["author_id","full_name","candidate_qid","label","description","birth_year","death_year","is_human","name_similarity","query_used","rank"])
        w.writeheader(); w.writerows(review)
    print(f"✳️ wrote {OUT_REVIEW}")
    print("👉 Open the review CSV, pick QIDs, then apply via wikidata_apply.py (or edit master).")

if __name__=="__main__":
    main()
