# tools/authors_split.py
#!/usr/bin/env python3
import sys, argparse, pathlib, yaml

def dump_author(author: dict) -> str:
    # 2-space indent, preserve key order, unicode allowed
    return yaml.safe_dump(author, sort_keys=False, allow_unicode=True, indent=2)

def main():
    ap = argparse.ArgumentParser(description="Split authors.master.yaml into one file per author")
    ap.add_argument("--master", default="citations/authors.master.yaml", help="Path to authors.master.yaml")
    ap.add_argument("--outdir", default="citations/authors", help="Output directory for split YAMLs")
    ap.add_argument("--clean", action="store_true", help="Delete existing *.yaml in outdir before writing")
    args = ap.parse_args()

    master = pathlib.Path(args.master)
    outdir = pathlib.Path(args.outdir)
    if not master.exists():
        print(f"ERROR: file not found: {master}", file=sys.stderr); sys.exit(2)

    try:
        data = yaml.safe_load(master.read_text())
    except Exception as e:
        print(f"ERROR: YAML load failed: {e}", file=sys.stderr); sys.exit(2)

    authors = data.get("authors")
    if not isinstance(authors, list) or not authors:
        print("ERROR: authors must be a non-empty list", file=sys.stderr); sys.exit(1)

    outdir.mkdir(parents=True, exist_ok=True)

    if args.clean:
        for f in outdir.glob("*.yaml"):
            f.unlink()

    written = 0
    for a in authors:
        aid = a.get("id")
        if not aid:
            print("ERROR: author missing id", file=sys.stderr); sys.exit(1)
        fn = outdir / f"{aid}.yaml"
        fn.write_text(dump_author(a))
        written += 1

    # keep directory tracked
    (outdir / ".gitkeep").touch(exist_ok=True)
    print(f"Wrote {written} author files to {outdir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
