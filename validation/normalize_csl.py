#!/usr/bin/env python3
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CIT_DIR = ROOT / "citations" / "registry"

REPLACEMENTS = {
    # standardize publisher-place abbreviations
    r"\bN\.Y\.\b": "NY",
    r"\bN\.J\.\b": "NJ",
    r"\bMd\.\b": "MD",
    r"\bCalif\.\b": "CA",
    r"\bVt\.\b": "VT",
    # unify language tag
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

        # drop nulls to keep files clean
        data = {k: v for k, v in data.items() if v is not None}

        data = order_keys(data)

        new = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
        old = jf.read_text(encoding="utf-8")
        if new != old:
            jf.write_text(new, encoding="utf-8")
            changed += 1
    print(f"Normalized {changed} file(s).")

if __name__ == "__main__":
    main()
