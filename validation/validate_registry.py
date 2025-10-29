#!/usr/bin/env python3
"""
Validate CSL-JSON registry entries (Bache Graph — LSDMU Bibliography).

Checks (errors cause non-zero exit):
  1) JSON-Schema (draft-07) validity
  2) filename <-> "id" match
  3) "id" format matches source:bache:LSDMU:bib:<slug>
  4) allowed topics (from topics.yaml) against x-bache.topics
  5) minimal required keys sanity
  6) duplicate IDs across files
  7) x-bache namespace/review_state/citation_shorthand sanity

Warnings (reported but do not fail):
  • missing "language"
  • "page" en-dash/em-dash usage (must be ASCII hyphen)
  • missing author/editor for citeable types
"""

import json
import sys
import re
from pathlib import Path

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError

try:
    import yaml
except Exception:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
CIT_DIR = ROOT / "citations" / "registry"
SCHEMA_PATH = ROOT / "schema" / "work.json"
TOPICS_PATH = ROOT / "topics.yaml"

REQUIRED_MIN_KEYS = {"id", "type", "title", "issued", "x-bache"}
ID_PATTERN = re.compile(r"^source:bache:LSDMU:bib:[a-z0-9\-]+$")  # stable, lowercase, hyphenated slug
REVIEW_STATES = {"draft", "steward-reviewed", "ratified"}

def load_schema():
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: Schema file not found: {SCHEMA_PATH}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON schema in {SCHEMA_PATH}: {e}", file=sys.stderr)
        sys.exit(2)

def load_allowed_topics():
    if not TOPICS_PATH.exists():
        return None  # whitelist not present; skip strict topic check
    if yaml is None:
        print("WARN: PyYAML not available; skipping topic whitelist check.", file=sys.stderr)
        return None
    try:
        data = yaml.safe_load(TOPICS_PATH.read_text(encoding="utf-8"))
        topics = data.get("topics") if isinstance(data, dict) else None
        if not topics:
            return None
        def kebab(s: str) -> str:
            s = s.strip().lower()
            s = re.sub(r"\s+", "-", s)
            s = re.sub(r"[^a-z0-9\-]+", "-", s)
            s = re.sub(r"-{2,}", "-", s).strip("-")
            return s
        return set(kebab(t) for t in topics if isinstance(t, str))
    except Exception as e:
        print(f"WARN: Could not parse topics whitelist from {TOPICS_PATH}: {e}", file=sys.stderr)
        return None

def iter_csl_files():
    for p in sorted(CIT_DIR.rglob("*.json")):
        yield p

def to_kebab(s: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9\-]+", "-", re.sub(r"\s+", "-", s.strip().lower()))).strip("-")

def shorthand_ok(sh: str) -> bool:
    """
    Accept patterns like:
      Family YYYY
      Family & Family YYYY
      Family et al. YYYY
    """
    pat = re.compile(
        r"^[A-Za-zÀ-ÖØ-öø-ÿ' .-]+(?: (?:&|et al\.) [A-Za-zÀ-ÖØ-öø-ÿ' .-]+)? \d{4}$"
    )
    return bool(pat.match(sh))

def ascii_hyphenated_pages(p: str) -> bool:
    # Pages must use ASCII hyphen '-' only (not en/em dashes)
    return bool(re.match(r"^\d+(-\d+)?$", p))

def validate_xbache(path: Path, data: dict, allowed_topics):
    errors = []
    warns = []

    xb = data.get("x-bache")
    if not isinstance(xb, dict):
        errors.append(f"{path}: x-bache must be an object")
        return errors, warns

    # namespace
    ns = xb.get("namespace")
    if ns != "bache":
        errors.append(f"{path}: x-bache.namespace must be 'bache', got '{ns}'")

    # review_state
    rs = xb.get("review_state")
    if rs and rs not in REVIEW_STATES:
        errors.append(f"{path}: x-bache.review_state '{rs}' not in {sorted(REVIEW_STATES)}")

    # citation_shorthand
    cs = xb.get("citation_shorthand")
    if cs and not shorthand_ok(cs):
        warns.append(f"{path}: WARN: x-bache.citation_shorthand looks unusual: '{cs}'")

    # topics whitelist (from x-bache.topics)
    topics = xb.get("topics", [])
    if topics is None:
        topics = []
    if not isinstance(topics, list):
        errors.append(f"{path}: x-bache.topics must be a list if present")
    else:
        for t in topics:
            if not isinstance(t, str):
                errors.append(f"{path}: x-bache.topic must be string, got {type(t).__name__}")
                continue
            t_k = to_kebab(t)
            if t_k != t:
                errors.append(f"{path}: x-bache.topic not kebab-case: '{t}' -> '{t_k}'")
            if allowed_topics is not None and t_k not in allowed_topics:
                errors.append(f"{path}: x-bache.topic '{t_k}' not in whitelist (topics.yaml)")

    # provenance sanity (optional but recommended)
    prov = xb.get("provenance")
    if prov is not None and not isinstance(prov, dict):
        errors.append(f"{path}: x-bache.provenance must be an object if present")

    return errors, warns

def validate_file(path: Path, validator: Draft7Validator, allowed_topics):
    errors = []
    warns = []

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(f"{path}: JSON parse error: {e}")
        return errors, warns, None

    # 1) schema
    for err in validator.iter_errors(data):
        loc = " > ".join(str(x) for x in err.path) if err.path else "(root)"
        errors.append(f"{path}: schema error at {loc}: {err.message}")

    # 2) filename <-> id
    expected_id = path.stem
    if data.get("id") != expected_id:
        errors.append(f"{path}: id mismatch: file='{expected_id}' json='{data.get('id')}'")

    # 3) id format
    idv = data.get("id")
    if isinstance(idv, str) and not ID_PATTERN.match(idv):
        errors.append(f"{path}: id format invalid, expected 'source:bache:LSDMU:bib:<slug>' lowercase-hyphenated; got '{idv}'")

    # 4) minimal keys guard
    missing = [k for k in REQUIRED_MIN_KEYS if k not in data]
    if missing:
        errors.append(f"{path}: missing minimal required keys: {missing}")

    # 5) x-bache validation (topics, namespace, review_state, shorthand)
    xb_errs, xb_warns = validate_xbache(path, data, allowed_topics)
    errors.extend(xb_errs)
    warns.extend(xb_warns)

    # 6) "language" recommended
    if "language" not in data:
        warns.append(f"{path}: WARN: missing 'language' (default is 'en' if unknown)")

    # 7) page ASCII hyphen check
    if "page" in data:
        pagev = data["page"]
        if isinstance(pagev, str) and not ascii_hyphenated_pages(pagev):
            warns.append(f"{path}: WARN: 'page' should use ASCII hyphen and digits only (e.g., '175-208'); got '{pagev}'")

    # 8) author/editor presence (soft check)
    typ = data.get("type")
    if typ not in {"webpage", "report"}:
        if not data.get("author") and not data.get("editor"):
            warns.append(f"{path}: WARN: missing 'author' and 'editor'")

    return errors, warns, data

def main():
    schema = load_schema()
    validator = Draft7Validator(schema)

    allowed_topics = load_allowed_topics()
    all_errors = []
    all_warns = []
    seen_ids = {}
    count = 0

    for path in iter_csl_files():
        count += 1
        errs, warns, data = validate_file(path, validator, allowed_topics)
        all_errors.extend(errs)
        all_warns.extend(warns)
        if data and "id" in data:
            this_id = data["id"]
            seen_ids.setdefault(this_id, []).append(str(path))

    # 9) duplicate IDs
    dupes = {k: v for k, v in seen_ids.items() if len(v) > 1}
    for id_, files in dupes.items():
        all_errors.append(f"DUPLICATE id '{id_}' in files: {', '.join(files)}")

    # Output
    if all_warns:
        print("\n".join(all_warns))

    if all_errors:
        print("\n".join(all_errors))
        print(f"\nFAILED: {len(all_errors)} error(s) across {count} file(s).")
        sys.exit(1)
    else:
        ok_msg = f"OK: {count} CSL-JSON file(s) validated successfully."
        if all_warns:
            ok_msg += f" ({len(all_warns)} warning(s) reported)"
        print(ok_msg)

if __name__ == "__main__":
    main()