#!/usr/bin/env python3
"""
Validate CSL-JSON registry entries.

Checks:
  1) JSON-Schema (draft-07) validity
  2) filename <-> "id" match
  3) allowed topics (from topics.yaml) if present
  4) duplicate IDs across files
  5) minimal required keys sanity
"""

import json
import sys
import re
from pathlib import Path

# jsonschema >= 4 exposes Draft7Validator
from jsonschema import Draft7Validator  # <-- fix: Draft7, not Draft07
from jsonschema.exceptions import ValidationError

try:
    import yaml
except Exception:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
CIT_DIR = ROOT / "citations" / "registry"
SCHEMA_PATH = ROOT / "schema" / "work.json"
TOPICS_PATH = ROOT / "topics.yaml"

REQUIRED_MIN_KEYS = {"id", "type", "title", "issued"}  # schema enforces more; this is just an extra guard


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
        return None  # no whitelist; skip
    if yaml is None:
        print("WARN: PyYAML not available; skipping topic whitelist check.", file=sys.stderr)
        return None
    try:
        data = yaml.safe_load(TOPICS_PATH.read_text(encoding="utf-8"))
        topics = data.get("topics") if isinstance(data, dict) else None
        if not topics:
            return None
        # normalize to kebab-case (matches normalizer)
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


def validate_file(path: Path, validator: Draft7Validator, allowed_topics):
    errors = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"{path}: JSON parse error: {e}")
        return errors, None

    # 1) schema
    for err in validator.iter_errors(data):
        # compact path for readability
        loc = " > ".join(str(x) for x in err.path) if err.path else "(root)"
        errors.append(f"{path}: schema error at {loc}: {err.message}")

    # 2) filename <-> id
    expected_id = path.stem
    if data.get("id") != expected_id:
        errors.append(f"{path}: id mismatch: file='{expected_id}' json='{data.get('id')}'")

    # 3) allowed topics
    if allowed_topics is not None:
        topics = data.get("topics") or []
        if not isinstance(topics, list):
            errors.append(f"{path}: topics must be a list if present")
        else:
            for t in topics:
                if not isinstance(t, str):
                    errors.append(f"{path}: topic must be string, got {type(t).__name__}")
                    continue
                # kebab-case check
                t_kebab = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9\-]+", "-", re.sub(r"\s+", "-", t.strip().lower()))).strip("-")
                if t_kebab != t:
                    errors.append(f"{path}: topic not kebab-case: '{t}' -> '{t_kebab}'")
                if t_kebab not in allowed_topics:
                    errors.append(f"{path}: topic '{t_kebab}' not in whitelist (topics.yaml)")

    # 4) minimal keys guard (friendly message before schema details)
    missing = [k for k in REQUIRED_MIN_KEYS if k not in data]
    if missing:
        errors.append(f"{path}: missing minimal required keys: {missing}")

    return errors, data


def main():
    schema = load_schema()
    validator = Draft7Validator(schema)  # <-- fix here

    allowed_topics = load_allowed_topics()
    all_errors = []
    seen_ids = {}
    count = 0

    for path in iter_csl_files():
        count += 1
        errs, data = validate_file(path, validator, allowed_topics)
        all_errors.extend(errs)
        if data and "id" in data:
            this_id = data["id"]
            seen_ids.setdefault(this_id, []).append(str(path))

    # 5) duplicate IDs
    dupes = {k: v for k, v in seen_ids.items() if len(v) > 1}
    for id_, files in dupes.items():
        all_errors.append(f"DUPLICATE id '{id_}' in files: {', '.join(files)}")

    if all_errors:
        print("\n".join(all_errors))
        print(f"\nFAILED: {len(all_errors)} error(s) across {count} file(s).")
        sys.exit(1)
    else:
        print(f"OK: {count} CSL-JSON file(s) validated successfully.")


if __name__ == "__main__":
    main()