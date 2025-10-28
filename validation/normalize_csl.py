#!/usr/bin/env python3
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CIT_DIR = ROOT / "citations" / "registry"

REPLACEMENTS = {
    r"\bN\.Y\.\b": "NY",
    r"\bN\.J\.\b": "NJ",
    r"\bMd\.\b": "MD",
    r"\bCalif\.\b": "CA",
    r"\bVt\.\b": "VT",
}

KEY_ORDER = [
    "id", "type", "title", "container-title", "author", "editor",
    "issued", "publisher", "publisher-place", "collection-title",
    "volume", "issue", "page", "container-number", "DOI", "ISBN",
    "URL", "language", "source", "topics", "notes"
]

def order_keys(d):
    out = {}
    for k in KEY_ORDER:
        if k in d:
            out[k] = d[k]
    for k,v in d.items():
        if k not in out:
            out[k] = v
    return out

def norm_place(s):
    if not s:
        return s
    t = s
    for pat, repl in REPLACEMENTS.items():
        t = re.sub(pat, repl, t)
    return t

def ensure_language(d):
    if "language" not in d or not d["language"]:
        d["language"] = "en"

def ensure_source(d):
    if "source" not in d:
        d["source"] = "LSDMU bibliography"

def ensure_topics_array(d):
    if "topics" in d and isinstance(d["topics"], str):
        d["topics"] = [d["topics"]]

def kebabify_topic(t: str) -> str:
    # trim, collapse whitespace to hyphens, keep a–z0–9 and hyphens
    t = t.strip()
    # common uppercase acronyms → lowercase
    t = t.lower()
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"[^a-z0-9\-]+", "-", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t

def normalize_topics(d):
    if "topics" not in d or not d["topics"]:
        return
    if not isinstance(d["topics"], list):
        return
    d["topics"] = sorted(set(kebabify_topic(t) for t in d["topics"] if isinstance(t, str) and t.strip()))

def drop_nulls(d):
    return {k: v for k, v in d.items() if v is not None}

def main():
    changed = 0
    for jf in sorted(CIT_DIR.rglob("*.json")):
        data = json.loads(jf.read_text(encoding="utf-8"))

        # normalize publisher-place
        if "publisher-place" in data and isinstance(data["publisher-place"], str):
            data["publisher-place"] = norm_place(data["publisher-place"])

        ensure_language(data)
        ensure_source(data)
        ensure_topics_array(data)
        normalize_topics(data)

        data = drop_nulls(data)
        data = order_keys(data)

        new = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
        if new != jf.read_text(encoding="utf-8"):
            jf.write_text(new, encoding="utf-8")
            changed += 1
    print(f"Normalized {changed} file(s).")

if __name__ == "__main__":
    main()