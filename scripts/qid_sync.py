#!/usr/bin/env python3
from __future__ import annotations
import json, sys, subprocess, datetime, os
from pathlib import Path

def repo_root() -> Path:
    # Prefer the git repo root; fall back to scripts/..
    try:
        p = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
        return Path(p)
    except Exception:
        return Path(__file__).resolve().parents[1]

ROOT = repo_root()

def detect_meta_path(root: Path) -> Path:
    # Env var wins; otherwise try common locations
    candidates = [
        os.environ.get("BA_META", ""),
        root / "meta" / "wikidata.jsonld",
        root / "bache-archive-meta" / "wikidata.jsonld",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    return root / "meta" / "wikidata.jsonld"  # default (will error if missing)

META_PATH: Path = detect_meta_path(ROOT)
BIB_DIR:   Path = Path(os.environ.get("BA_BIB", ROOT / "citations" / "source" / "bache" / "LSDMU" / "bib"))

# Map filename substrings → meta entity keys (extend as needed)
WORK_KEY_BY_SUBSTR = {
    "bache-1990-lifecycles": "lifecycles",
    "bache-2000-dark-night-early-dawn": "dark_night_early_dawn",
    "bache-2008-living-classroom": "living_classroom",
    # Add the 2019 record when present, e.g.:
    # "bache-2019-lsd-and-the-mind-of-the-universe": "lsdmu",
}

def short_git_rev(path: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(path.parent), "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "HEAD"

def load_meta() -> dict:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    ents = meta.get("entities", {})
    # Strip 'wd:' → keep bare QIDs
    return {k: (v.split("wd:")[1] if isinstance(v, str) and v.startswith("wd:") else v) for k, v in ents.items()}

def find_work_key(fname: str) -> str | None:
    for substr, key in WORK_KEY_BY_SUBSTR.items():
        if substr in fname:
            return key
    return None

def is_bache_person(p: dict) -> bool:
    fam = (p.get("family") or "").strip().lower()
    giv = (p.get("given") or "").strip().lower()
    return fam == "bache" and giv.startswith("christopher")

def ensure_x_bache(d: dict) -> dict:
    xb = d.get("x-bache")
    if not isinstance(xb, dict):
        xb = {}
        d["x-bache"] = xb
    return xb

def merge_provenance(xb: dict, meta_commit: str):
    prov = xb.get("provenance") or {}
    prov.update({
        "meta_ref": str(Path("meta") / "wikidata.jsonld") if "meta" in str(META_PATH) else "bache-archive-meta/wikidata.jsonld",
        "meta_commit": meta_commit,
        "resolved_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    })
    xb["provenance"] = prov

def sync_file(p: Path, meta_qids: dict, meta_commit: str) -> bool:
    data = json.loads(p.read_text(encoding="utf-8"))
    changed = False

    # Author QID (Christopher M. Bache)
    author_qid = meta_qids.get("christopher_m_bache")
    if author_qid:
        for person in (data.get("author") or []):
            if is_bache_person(person):
                xb = ensure_x_bache(person)
                if xb.get("wikidata") != author_qid:
                    xb["wikidata"] = author_qid
                    changed = True

    # Work QID via filename mapping
    wk = find_work_key(p.name)
    if wk:
        work_qid = meta_qids.get(wk)
        if work_qid:
            xb = ensure_x_bache(data)
            if xb.get("wikidata") != work_qid:
                xb["wikidata"] = work_qid
                changed = True
            before = json.dumps(xb.get("provenance", {}), sort_keys=True)
            merge_provenance(xb, meta_commit)
            after  = json.dumps(xb.get("provenance", {}), sort_keys=True)
            if before != after:
                changed = True

    if changed:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed

def main() -> int:
    errs = []
    if not META_PATH.exists():
        errs.append(f"meta file not found: {META_PATH}")
    if not BIB_DIR.exists():
        errs.append(f"bib dir not found: {BIB_DIR}")
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 1

    meta_qids = load_meta()
    meta_commit = short_git_rev(META_PATH)

    total = changed = 0
    for fp in sorted(BIB_DIR.glob("*.json")):
        total += 1
        if sync_file(fp, meta_qids, meta_commit):
            print(f"updated: {fp.relative_to(ROOT)}")
            changed += 1
    print(f"Done. {changed}/{total} files updated.")
    return 0

if __name__ == "__main__":
    sys.exit(main())