#!/usr/bin/env python3
import json, sys, re, os
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("Please install jsonschema: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
CIT_DIR = ROOT / "citations" / "registry"
SCHEMA = ROOT / "schema" / "work.json"
TOPICS = ROOT / "topics.yaml"
AUTHORS_DIR = ROOT / "citations" / "authors"

# --- small YAML loader without pyyaml dependency ---
def load_topics_yaml(fp: Path):
    topics = set()
    if not fp.exists():
        return topics
    for line in fp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # naive parse: lines like "- psychedelics" or " - psychedelics"
        m = re.match(r"^-+\s*([A-Za-z0-9._:-]+)", line)
        if m:
            topics.add(m.group(1))
        else:
            # lines like "psychedelics:" or "psychedelics"
            m2 = re.match(r"^([A-Za-z0-9._:-]+):?$", line)
            if m2:
                topics.add(m2.group(1))
    return topics

def slug_from_path(p: Path):
    return p.stem  # filename without .json

def main():
    # Load schema
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Cannot read schema {SCHEMA}: {e}", file=sys.stderr)
        sys.exit(1)

    # Load topic whitelist (optional)
    allowed_topics = load_topics_yaml(TOPICS)

    validator = jsonschema.Draft07Validator(schema)

    json_files = sorted(CIT_DIR.rglob("*.json"))
    if not json_files:
        print("[WARN] No JSON files found under citations/registry")
        sys.exit(0)

    ids_seen = {}
    errors = 0

    for jf in json_files:
        rel = jf.relative_to(ROOT)
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[FAIL] {rel}: invalid JSON: {e}")
            errors += 1
            continue

        # JSON-Schema validation
        errs = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errs:
            print(f"[FAIL] {rel}: schema errors:")
            for e in errs:
                loc = " / ".join(map(str, e.path)) or "<root>"
                print(f"  - {loc}: {e.message}")
            errors += 1

        # filename must start with id
        expected = slug_from_path(jf)
        if data.get("id") != expected:
            print(f"[FAIL] {rel}: id '{data.get('id')}' must equal filename slug '{expected}'")
            errors += 1

        # duplicate id detection
        if data.get("id") in ids_seen:
            print(f"[FAIL] {rel}: duplicate id also in {ids_seen[data['id']]}")
            errors += 1
        else:
            ids_seen[data.get("id")] = rel

        # topics must be in whitelist if whitelist present
        topics = data.get("topics", [])
        if allowed_topics:
            bad = [t for t in topics if t not in allowed_topics]
            if bad:
                print(f"[FAIL] {rel}: topics not in whitelist: {bad}")
                errors += 1

        # check that every listed author surname likely has an author profile (best-effort heuristic)
        # We expect an authors YAML named '<surname-kebab>|<surname-given>.yaml'—we’ll just check surname file presence as a hint
        for a in data.get("author", []):
            fam = a.get("family", "").strip().lower()
            if not fam:
                continue
            kebab = re.sub(r"[^a-z0-9]+", "-", fam).strip("-")
            # allow any one of several variants to exist
            candidates = list(AUTHORS_DIR.glob(f"{kebab}*.yaml"))
            if not candidates:
                print(f"[WARN] {rel}: no author YAML candidate found for family='{fam}'")

    if errors:
        print(f"\nValidation failed with {errors} error(s).")
        sys.exit(1)
    else:
        print("All citation files passed validation ✔")

if __name__ == "__main__":
    main()
