# tools/orcid_candidates.py  (patched)
#!/usr/bin/env python3
import csv, json, time, pathlib, re, sys
from typing import Dict, List, Optional
import requests
import yaml

AUTH_MASTER = pathlib.Path("citations/authors.master.yaml")
OUT_CSV = pathlib.Path("citations/_manifests/orcid_candidates.csv")
CACHE = pathlib.Path("citations/_cache/orcid_http.jsonl")
CACHE.parent.mkdir(parents=True, exist_ok=True)
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# Set a polite UA and request JSON everywhere
UA = {
    "User-Agent": "lsdmu-bibliography/1.0 (ORCID discovery; contact: bibliography-team)",
    "Accept": "application/json",
}

def http_get(url: str, params: dict=None, sleep=0.6, retries=3):
    """GET with tiny cache, Accept JSON, and basic retry/backoff."""
    key = {"url": url, "params": params or {}}
    kstr = json.dumps(key, sort_keys=True)

    # cache lookup
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
            status = r.status_code
            if status == 429:
                # rate-limited; backoff and retry
                time.sleep(1.5 * attempt)
                continue
            if status >= 400:
                # log and raise
                sys.stderr.write(f"[http {status}] {url} {params or ''}\n{r.text[:300]}\n")
                r.raise_for_status()

            # Try parse JSON only if header says JSON; otherwise attempt anyway with guard
            ctype = r.headers.get("Content-Type","").lower()
            if "json" in ctype:
                data = r.json()
            else:
                # fallback try
                try:
                    data = r.json()
                except Exception:
                    # store raw text to cache to avoid repeated failing calls
                    data = {"_raw": r.text}

            # cache store
            with CACHE.open("a") as f:
                f.write(json.dumps({"key": kstr, "data": data}) + "\n")

            time.sleep(sleep)
            return data

        except Exception as e:
            last_err = e
            # small incremental backoff
            time.sleep(0.8 * attempt)

    # if we got here, all retries failed
    raise last_err

def norm(s): return re.sub(r"\s+", " ", (s or "").strip()).lower()

def openalex_candidates(name: str) -> List[Dict]:
    url = "https://api.openalex.org/authors"
    # FIX: per_page (underscore), not per-page
    data = http_get(url, params={"search": name, "per_page": 5})
    out = []
    for r in (data.get("results") or []):
        out.append({
            "source": "openalex",
            "display_name": r.get("display_name"),
            "orcid": r.get("orcid"),
            "works_count": r.get("works_count"),
            "institution": (r.get("last_known_institution") or {}).get("display_name"),
            "id": r.get("id"),
        })
    return out

def crossref_orcids_by_title(title: str) -> List[Dict]:
    if not title: return []
    url = "https://api.crossref.org/works"
    data = http_get(url, params={"query.title": title, "rows": 3})
    out = []
    items = (data.get("message") or {}).get("items", [])
    for it in items[:1]:  # top hit only
        for a in (it.get("author") or []):
            if "ORCID" in a:
                out.append({
                    "source": "crossref",
                    "display_name": f"{a.get('given','')} {a.get('family','')}".strip(),
                    "orcid": a.get("ORCID","").replace("https://orcid.org/",""),
                    "work_title": (it.get("title") or [None])[0],
                    "DOI": it.get("DOI")
                })
    return out

def orcid_expanded_search(name: str) -> List[Dict]:
    # ORCID needs Accept: application/json; handled in UA
    url = "https://pub.orcid.org/v3.0/expanded-search"
    data = http_get(url, params={"q": name})
    out = []
    # If ORCID returns non-JSON (shouldn’t anymore), we’ll get {"_raw": "..."}; guard here
    results = (data.get("expanded-result") or []) if isinstance(data, dict) else []
    for r in results:
        out.append({
            "source": "orcid",
            "display_name": r.get("display-name"),
            "orcid": r.get("orcid-id"),
            "institution": r.get("institution-name"),
        })
    return out

def main():
    master = yaml.safe_load(AUTH_MASTER.read_text())
    authors = master["authors"]

    rows = []
    for a in authors:
        if a.get("entity_type") != "person":
            continue
        full = a["full_name"]

        cands = []
        # 1) OpenAlex often gives ORCID directly
        cands.extend(openalex_candidates(full))

        # 2) Crossref via a representative work title (heuristic)
        if a.get("notable_works"):
            # Title guess: you can enhance by reading actual titles from citations/source
            title_guess = a["notable_works"][0].replace("-", " ")
            cands.extend(crossref_orcids_by_title(title_guess))

        # 3) ORCID expanded search fallback
        if not any(x.get("orcid") for x in cands):
            cands.extend(orcid_expanded_search(full))

        if not cands:
            rows.append({"author_id": a["id"], "full_name": full, "candidate_source": None,
                         "display_name": None, "orcid": None, "works_count": None,
                         "institution": None, "match_score_hint": 0})
            continue

        for c in cands:
            score = 0
            if c.get("orcid"): score += 5
            if norm(c.get("display_name")) == norm(full): score += 3
            if c.get("works_count"): 
                try: score += min(3, int((c["works_count"] or 0)/50)+1)
                except: pass
            rows.append({
                "author_id": a["id"],
                "full_name": full,
                "candidate_source": c.get("source"),
                "display_name": c.get("display_name"),
                "orcid": c.get("orcid"),
                "works_count": c.get("works_count"),
                "institution": c.get("institution"),
                "match_score_hint": score
            })

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "author_id","full_name","candidate_source","display_name","orcid","works_count","institution","match_score_hint"
        ])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote candidate list: {OUT_CSV}\nReview and copy the correct ORCID into authors.master.yaml.")

if __name__ == "__main__":
    main()
