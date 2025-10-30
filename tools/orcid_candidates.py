# tools/orcid_candidates.py  (drop-in replacement)
#!/usr/bin/env python3
import os, csv, json, time, pathlib, re, sys
from typing import Dict, List
import requests

try:
    import yaml
except Exception as e:
    print("Missing PyYAML. Install with: pip install pyyaml", file=sys.stderr); sys.exit(2)

# --------------------
# Config & paths
# --------------------
AUTH_MASTER = pathlib.Path(os.environ.get("AUTH_MASTER", "citations/authors.master.yaml"))
OUT_CSV     = pathlib.Path(os.environ.get("ORCID_CANDIDATES", "citations/_manifests/orcid_candidates.csv"))
CACHE       = pathlib.Path(os.environ.get("ORCID_HTTP_CACHE", "citations/_cache/orcid_http.jsonl"))
CACHE.parent.mkdir(parents=True, exist_ok=True)
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

UA = {
    "User-Agent": "lsdmu-bibliography/1.0 (ORCID discovery; contact: bibliography-team)",
    "Accept": "application/json",
}

ORCID_RE = re.compile(r'(?:https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$')
EN_DASH_HYPHEN = r'[\u2013-]'

# --------------------
# Helpers
# --------------------
def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def norm_lower(s: str) -> str:
    return norm_space(s).lower()

def parse_birth_year(lifespan: str|None):
    if not lifespan: return None
    m = re.match(rf'^\s*(\d{{3,4}})\s*{EN_DASH_HYPHEN}', lifespan)
    return int(m.group(1)) if m else None

def http_get(url: str, params: dict=None, sleep=0.5, retries=3):
    """GET with tiny JSONL cache, JSON Accept, and basic retry/backoff."""
    key = {"url": url, "params": params or {}}
    kstr = json.dumps(key, sort_keys=True)

    # Cache lookup
    if CACHE.exists():
        with CACHE.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec.get("key") == kstr:
                        return rec["data"]
                except Exception:
                    continue

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 429:
                time.sleep(1.2 * attempt)
                continue
            if r.status_code >= 400:
                sys.stderr.write(f"[http {r.status_code}] {url} {params or ''}\n{r.text[:300]}\n")
                r.raise_for_status()

            ctype = (r.headers.get("Content-Type") or "").lower()
            if "json" in ctype:
                data = r.json()
            else:
                try:
                    data = r.json()
                except Exception:
                    data = {"_raw": r.text}

            with CACHE.open("a") as f:
                f.write(json.dumps({"key": kstr, "data": data}) + "\n")

            time.sleep(sleep)
            return data
        except Exception as e:
            last_err = e
            time.sleep(0.7 * attempt)

    raise last_err

# --------------------
# Sources
# --------------------
def from_openalex(name: str) -> List[Dict]:
    """OpenAlex often surfaces ORCID directly."""
    url = "https://api.openalex.org/authors"
    data = http_get(url, params={"search": name, "per_page": 5})
    out = []
    for r in (data.get("results") or []):
        out.append({
            "source": "openalex",
            "display_name": r.get("display_name"),
            "orcid": (r.get("orcid") or "").replace("https://orcid.org/",""),
            "works_count": r.get("works_count"),
            "institution": (r.get("last_known_institution") or {}).get("display_name"),
            "id": r.get("id"),
        })
    return out

def from_crossref_title(title: str) -> List[Dict]:
    """Use a representative title (if known) to pull author ORCIDs."""
    if not title: return []
    url = "https://api.crossref.org/works"
    data = http_get(url, params={"query.title": title, "rows": 3})
    items = (data.get("message") or {}).get("items", [])
    out = []
    for it in items[:1]:  # top hit only (conservative)
        for a in (it.get("author") or []):
            orcid = a.get("ORCID") or ""
            m = ORCID_RE.search(orcid)
            if not m:
                continue
            out.append({
                "source": "crossref",
                "display_name": norm_space(f"{a.get('given','')} {a.get('family','')}"),
                "orcid": m.group(1),
                "works_count": None,
                "institution": None,
                "id": it.get("DOI"),
            })
    return out

def from_orcid_expanded(name: str) -> List[Dict]:
    """ORCID expanded search (broad but noisier)."""
    url = "https://pub.orcid.org/v3.0/expanded-search"
    data = http_get(url, params={"q": name})
    results = (data.get("expanded-result") or []) if isinstance(data, dict) else []
    out = []
    for r in results:
        out.append({
            "source": "orcid",
            "display_name": r.get("display-name"),
            "orcid": r.get("orcid-id"),
            "works_count": None,
            "institution": r.get("institution-name"),
            "id": None,
        })
    return out

# --------------------
# Scoring
# --------------------
def score_candidate(full_name: str, c: Dict) -> int:
    """Heuristic score: ORCID present, exact name match, works_count signal."""
    score = 0
    if c.get("orcid"): score += 5
    if norm_lower(c.get("display_name")) == norm_lower(full_name): score += 3
    wc = c.get("works_count")
    if isinstance(wc, int):
        score += min(3, wc // 50 + 1)  # coarse signal
    return score

# --------------------
# Main
# --------------------
def main():
    if not AUTH_MASTER.exists():
        print(f"ERROR: missing {AUTH_MASTER}", file=sys.stderr); return 2
    master = yaml.safe_load(AUTH_MASTER.read_text()) or {}
    authors = [a for a in master.get("authors", []) if a.get("entity_type") == "person"]

    rows = []
    for idx, a in enumerate(authors, 1):
        aid  = a.get("id")
        full = a.get("full_name") or ""
        lifespan = a.get("lifespan")
        birth = parse_birth_year(lifespan)

        # Skip clear historicals for ORCID discovery (pre-1900 unlikely to have real ORCIDs)
        if birth is not None and birth < 1900:
            rows.append({
                "author_id": aid,
                "full_name": full,
                "candidate_source": None,
                "display_name": None,
                "orcid": None,
                "works_count": None,
                "institution": None,
                "match_score_hint": 0
            })
            continue

        print(f"[{idx}/{len(authors)}] search: {full}")
        cands: List[Dict] = []

        # 1) OpenAlex
        cands.extend(from_openalex(full))

        # 2) Crossref via first notable work (best-effort)
        if a.get("notable_works"):
            # If you later store true titles, swap this placeholder with actual title lookup.
            title_guess = str(a["notable_works"][0]).replace("-", " ")
            cands.extend(from_crossref_title(title_guess))

        # 3) ORCID expanded search if still no ORCID present
        if not any(x.get("orcid") for x in cands):
            cands.extend(from_orcid_expanded(full))

        if not cands:
            rows.append({
                "author_id": aid,
                "full_name": full,
                "candidate_source": None,
                "display_name": None,
                "orcid": None,
                "works_count": None,
                "institution": None,
                "match_score_hint": 0
            })
            continue

        for c in cands:
            rows.append({
                "author_id": aid,
                "full_name": full,
                "candidate_source": c.get("source"),
                "display_name": c.get("display_name"),
                "orcid": (c.get("orcid") or "").replace("https://orcid.org/",""),
                "works_count": c.get("works_count"),
                "institution": c.get("institution"),
                "match_score_hint": score_candidate(full, c),
            })

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "author_id","full_name","candidate_source","display_name","orcid","works_count","institution","match_score_hint"
        ])
        w.writeheader()
        w.writerows(rows)

    print(f"✳️ wrote {OUT_CSV}")

if __name__ == "__main__":
    sys.exit(main())