#!/usr/bin/env python3
import json, re
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[1]
CIT_DIR = ROOT / "citations" / "registry"

# Abbreviation / normalization maps
PLACE_REPLACEMENTS = {
    r"\bN\.Y\.\b": "NY",
    r"\bN\.J\.\b": "NJ",
    r"\bMd\.\b": "MD",
    r"\bMass\.\b": "MA",
    r"\bCalif\.\b": "CA",
    r"\bColo\.\b": "CO",
    r"\bWash\.\b": "WA",
    r"\bMinn\.\b": "MN",
    r"\bMich\.\b": "MI",
    r"\bIll\.\b": "IL",
    r"\bInd\.\b": "IN",
    r"\bVa\.\b": "VA",
    r"\bPa\.\b": "PA",
    r"\bVt\.\b": "VT",
    r"\bGa\.\b": "GA",
    r"\bAla\.\b": "AL",
    r"\bTenn\.\b": "TN",
    r"\bAriz\.\b": "AZ",
    r"\bN\.M\.\b": "NM",
    r"\bB\.C\.\b": "BC",
    r"\bOnt\.\b": "ON",
    r"\bQue\.\b": "QC",
}

PUBLISHER_REPLACEMENTS = {
    # Light-touch brand normalization; add more as desired
    "Harper Collins": "HarperCollins",
    "Harper Collins Publishers": "HarperCollins",
    "Random House": "Random House",
    "Bell Tower/Random House": "Bell Tower/Random House",
    "Penguin Books": "Penguin",
    "J. P. Tarcher": "J. P. Tarcher",
    "Jeremy Tarcher/ Putnam": "Jeremy Tarcher/Putnam",
    "Jeremy Tarcher/Putnam": "Jeremy Tarcher/Putnam",
    "Chelsea Green Publishing Co.": "Chelsea Green Publishing",
    "Chelsea Green Publishing Co": "Chelsea Green Publishing",
}

# Ensure key order includes x-bache and common CSL fields; no deprecated top-level topics/source
KEY_ORDER = [
    "id", "type", "title", "container-title",
    "author", "editor", "issued", "original-date",
    "publisher", "publisher-place", "collection-title",
    "volume", "issue", "page", "container-number",
    "DOI", "ISBN", "URL", "language", "x-bache",
    "notes"
]

ID_PATTERN = re.compile(r"^source:bache:LSDMU:bib:[a-z0-9\-]+$")

def order_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k in KEY_ORDER:
        if k in d:
            out[k] = d[k]
    for k, v in d.items():
        if k not in out:
            out[k] = v
    return out

def norm_place(s: str) -> str:
    if not s or not isinstance(s, str):
        return s
    t = s
    for pat, repl in PLACE_REPLACEMENTS.items():
        t = re.sub(pat, repl, t)
    # Collapse multiple spaces and standardize comma+space
    t = re.sub(r"\s*,\s*", ", ", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" ,")
    return t

def norm_publisher(s: str) -> str:
    if not s or not isinstance(s, str):
        return s
    s2 = s.strip()
    return PUBLISHER_REPLACEMENTS.get(s2, s2)

def ensure_language(d: Dict[str, Any]) -> None:
    if "language" not in d or not d["language"]:
        d["language"] = "en"

def clean_string(v: Any) -> Any:
    if isinstance(v, str):
        # Trim and collapse whitespace
        vv = re.sub(r"\s{2,}", " ", v.strip())
        return vv
    return v

def deep_clean_strings(d: Any) -> Any:
    if isinstance(d, dict):
        return {k: deep_clean_strings(v) for k, v in d.items()}
    if isinstance(d, list):
        return [deep_clean_strings(x) for x in d]
    return clean_string(d)

def ensure_xbache(d: Dict[str, Any]) -> None:
    xb = d.get("x-bache")
    if not isinstance(xb, dict):
        xb = {}
        d["x-bache"] = xb
    # Namespace required
    if xb.get("namespace") != "bache":
        xb["namespace"] = "bache"
    # Review state default
    if "review_state" not in xb or not xb["review_state"]:
        xb["review_state"] = "draft"

def ensure_topics_into_xbache(d: Dict[str, Any]) -> None:
    # Accept legacy top-level "topics", migrate into x-bache.topics
    legacy = d.get("topics")
    if legacy:
        if isinstance(legacy, str):
            legacy_list = [legacy]
        elif isinstance(legacy, list):
            legacy_list = legacy
        else:
            legacy_list = []
    else:
        legacy_list = []

    xb = d.get("x-bache")
    if not isinstance(xb, dict):
        xb = {}
        d["x-bache"] = xb

    # Normalize existing x-bache.topics + legacy
    merged: List[str] = []
    if isinstance(xb.get("topics"), list):
        merged.extend(xb["topics"])
    merged.extend(legacy_list)

    def kebabify_topic(t: str) -> str:
        t = t.strip().lower()
        t = re.sub(r"\s+", "-", t)
        t = re.sub(r"[^a-z0-9\-]+", "-", t)
        t = re.sub(r"-{2,}", "-", t).strip("-")
        return t

    merged = [kebabify_topic(t) for t in merged if isinstance(t, str) and t.strip()]
    # De-duplicate and sort
    merged = sorted(set(merged))
    if merged:
        xb["topics"] = merged
    elif "topics" in xb:
        # If empty result, drop empty list to keep JSON clean
        if not xb["topics"]:
            xb.pop("topics", None)

    # Drop deprecated top-level topics
    d.pop("topics", None)

def drop_nulls(d: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, dict):
            vv = drop_nulls(v)
            if vv != {}:
                out[k] = vv
        elif isinstance(v, list):
            vv = []
            for item in v:
                if isinstance(item, dict):
                    dd = drop_nulls(item)
                    if dd != {}:
                        vv.append(dd)
                elif item is not None:
                    vv.append(item)
            out[k] = vv
        else:
            out[k] = v
    return out

def normalize_page_hyphens(d: Dict[str, Any]) -> None:
    p = d.get("page")
    if isinstance(p, str):
        # replace en/em dashes with ASCII hyphen
        p2 = p.replace("\u2013", "-").replace("\u2014", "-")
        p2 = re.sub(r"\s*-\s*", "-", p2).strip()
        d["page"] = p2

def normalize_urls(d: Dict[str, Any]) -> None:
    url = d.get("URL")
    if isinstance(url, str):
        d["URL"] = url.strip()

def normalize_ids(d: Dict[str, Any], jf: Path) -> None:
    # Keep id as-is, but if it's missing or clearly wrong, set to filename stem
    stem = jf.stem
    idv = d.get("id")
    if not isinstance(idv, str) or not ID_PATTERN.match(idv):
        d["id"] = stem  # filename should already be canonical per your pipeline

def normalize_people(d: Dict[str, Any]) -> None:
    # Clean strings inside author/editor person objects; do not guess particles
    for key in ("author", "editor", "interviewer"):
        if isinstance(d.get(key), list):
            cleaned = []
            for person in d[key]:
                if isinstance(person, dict):
                    person = {
                        k: clean_string(v) if isinstance(v, str) else v
                        for k, v in person.items()
                    }
                cleaned.append(person)
            d[key] = cleaned

def normalize_publisher_and_place(d: Dict[str, Any]) -> None:
    if "publisher" in d and isinstance(d["publisher"], str):
        d["publisher"] = norm_publisher(d["publisher"])
    if "publisher-place" in d and isinstance(d["publisher-place"], str):
        d["publisher-place"] = norm_place(d["publisher-place"])

def main():
    changed = 0
    for jf in sorted(CIT_DIR.rglob("*.json")):
        raw_text = jf.read_text(encoding="utf-8")
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Leave parse errors to validator; skip rewriting
            continue

        # Deep tidy of stray whitespace
        data = deep_clean_strings(data)

        # Normalize IDs (non-destructive if already correct)
        normalize_ids(data, jf)

        # Language default
        ensure_language(data)

        # x-bache presence + migrate topics
        ensure_xbache(data)
        ensure_topics_into_xbache(data)

        # Normalize publisher & place
        normalize_publisher_and_place(data)

        # Page hyphens and URL tidying
        normalize_page_hyphens(data)
        normalize_urls(data)

        # People fields
        normalize_people(data)

        # Drop deprecated top-level keys
        data.pop("source", None)  # legacy
        # (top-level "topics" already removed in ensure_topics_into_xbache)

        # Drop nulls and order keys
        data = drop_nulls(data)
        data = order_keys(data)

        new_text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
        if new_text != raw_text:
            jf.write_text(new_text, encoding="utf-8")
            changed += 1

    print(f"Normalized {changed} file(s).")

if __name__ == "__main__":
    main()