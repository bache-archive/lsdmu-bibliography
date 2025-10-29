# tools/authors_validate.py
#!/usr/bin/env python3
import sys, argparse, pathlib, yaml

REQUIRED_TOP = ("version","package_curator","package_created_at","authors")
REQUIRED_ORDER = [
    "id","entity_type","full_name","family","given","lifespan","nationality",
    "fields","wikidata","orcid","aliases","notable_works","notes",
    "review_state","curator","created_at"
]

def main():
    ap = argparse.ArgumentParser(description="Validate authors.master.yaml")
    ap.add_argument("--master", default="citations/authors.master.yaml", help="Path to authors.master.yaml")
    args = ap.parse_args()

    p = pathlib.Path(args.master)
    if not p.exists():
        print(f"ERROR: file not found: {p}", file=sys.stderr); sys.exit(2)

    try:
        data = yaml.safe_load(p.read_text())
    except Exception as e:
        print(f"ERROR: YAML load failed: {e}", file=sys.stderr); sys.exit(2)

    if not isinstance(data, dict):
        print("ERROR: top-level must be a mapping", file=sys.stderr); sys.exit(1)

    for k in REQUIRED_TOP:
        if k not in data:
            print(f"ERROR: missing top-level key: {k}", file=sys.stderr); sys.exit(1)

    authors = data["authors"]
    if not isinstance(authors, list) or not authors:
        print("ERROR: authors must be a non-empty list", file=sys.stderr); sys.exit(1)

    seen = set()
    for idx, a in enumerate(authors, 1):
        if not isinstance(a, dict):
            print(f"ERROR: author #{idx} is not a mapping", file=sys.stderr); sys.exit(1)
        # keys present
        for k in REQUIRED_ORDER:
            if k not in a:
                aid = a.get("id")
                print(f"ERROR: author #{idx} ({aid}) missing key: {k}", file=sys.stderr); sys.exit(1)
        # duplicate id
        aid = a["id"]
        if aid in seen:
            print(f"ERROR: duplicate author id: {aid}", file=sys.stderr); sys.exit(1)
        seen.add(aid)

    print(f"OK: {len(authors)} authors validated in {p}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
