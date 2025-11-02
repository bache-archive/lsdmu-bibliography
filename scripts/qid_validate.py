#!/usr/bin/env python3
from __future__ import annotations
import json, sys, os, subprocess
from pathlib import Path

def repo_root() -> Path:
    try:
        p = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
        return Path(p)
    except Exception:
        return Path(__file__).resolve().parents[1]

ROOT = repo_root()

def detect_meta_path(root: Path) -> Path:
    candidates = [
        os.environ.get("BA_META", ""),
        root / "meta" / "wikidata.jsonld",
        root / "bache-archive-meta" / "wikidata.jsonld",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    return root / "meta" / "wikidata.jsonld"

META_PATH: Path = detect_meta_path(ROOT)
BIB_DIR:   Path = Path(os.environ.get("BA_BIB", ROOT / "citations" / "source" / "bache" / "LSDMU" / "bib"))

WORK_KEY_BY_SUBSTR = {
    "bache-1990-lifecycles": "lifecycles",
    "bache-2000-dark-night-early-dawn": "dark_night_early_dawn",
    "bache-2008-living-classroom": "living_classroom",
    # Add the 2019 record when present:
    # "bache-2019-lsd-and-the-mind-of-the-universe": "lsdmu",
}

def load_meta() -> dict:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    ents = meta.get("entities", {})
    return {k: (v.split("wd:")[1] if isinstance(v, str) and v.startswith("wd:") else v) for k, v in ents.items()}

def is_bache_person(p: dict) -> bool:
    fam = (p.get("family") or "").strip().lower()
    giv = (p.get("given") or "").strip().lower()
    return fam == "bache" and giv.startswith("christopher")

def find_work_key(fname: str) -> str | None:
    for substr, key in WORK_KEY_BY_SUBSTR.items():
        if substr in fname:
            return key
    return None

def main() -> int:
    errs = []
    if not META_PATH.exists():
        errs.append(f"meta file missing: {META_PATH}")
    if not BIB_DIR.exists():
        errs.append(f"bib dir missing: {BIB_DIR}")
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 2

    meta_q = load_meta()
    a_qid = meta_q.get("christopher_m_bache")
    if not a_qid:
        errs.append("missing author QID for christopher_m_bache in meta")

    for fp in sorted(BIB_DIR.glob("*.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))

        # Author QID check
        for person in (data.get("author") or []):
            if is_bache_person(person):
                have = ((person.get("x-bache") or {}).get("wikidata"))
                if have != a_qid:
                    errs.append(f"{fp.name}: author QID mismatch (have={have}, want={a_qid})")

        # Work QID check
        wk = find_work_key(fp.name)
        if wk:
            want = meta_q.get(wk)
            have = ((data.get("x-bache") or {}).get("wikidata"))
            if have != want:
                errs.append(f"{fp.name}: work QID mismatch (have={have}, want={want})")

    if errs:
        print("QID validation errors:", file=sys.stderr)
        print("\n".join(f"- {e}" for e in errs), file=sys.stderr)
        return 1

    print("QID validation passed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())