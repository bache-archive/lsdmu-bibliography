#!/usr/bin/env python3
"""
Split a JSONL registry into component JSON files laid out by the colon-delimited `id`.

Example:
  python split_jsonl.py registry.jsonl outdir
  python split_jsonl.py registry.jsonl outdir --dry-run
  python split_jsonl.py registry.jsonl outdir --overwrite

Behavior:
- Each JSON object must contain "id": "<colon:separated:path:basename>".
- Creates: <outdir>/<colon parts as dirs>/<basename>.json
- Pretty-prints with indent=2, ensures trailing newline.
- Writes outdir/_manifests/outputs.txt and checksums.sha256
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9._-]+")

def sanitize_segment(seg: str) -> str:
    # Replace any unsafe chars with '-'
    s = SAFE_SEGMENT_RE.sub("-", seg.strip())
    # Avoid empty names
    return s if s else "_"

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", help="Input JSONL file")
    ap.add_argument("outdir", help="Output directory (created if missing)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    ap.add_argument("--dry-run", action="store_true", help="Print actions, do not write files")
    ap.add_argument("--indent", type=int, default=2, help="JSON indent (default: 2)")
    args = ap.parse_args()

    in_path = Path(args.jsonl)
    out_root = Path(args.outdir)

    if not in_path.exists():
        print(f"ERROR: Input not found: {in_path}", file=sys.stderr)
        sys.exit(2)

    # Ensure output base exists (except in dry-run)
    if not args.dry_run:
        out_root.mkdir(parents=True, exist_ok=True)

    outputs = []
    ids_seen = set()
    errors = 0
    n = 0

    with in_path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            n += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"ERROR:{ln}: invalid JSON: {e}", file=sys.stderr)
                errors += 1
                continue

            jid = obj.get("id")
            if not isinstance(jid, str) or not jid:
                print(f"ERROR:{ln}: object missing string 'id'", file=sys.stderr)
                errors += 1
                continue

            if jid in ids_seen:
                if not args.overwrite:
                    print(f"ERROR:{ln}: duplicate id '{jid}' (use --overwrite to allow)", file=sys.stderr)
                    errors += 1
                    continue
            ids_seen.add(jid)

            parts = [sanitize_segment(p) for p in jid.split(":")]
            if len(parts) < 2:
                print(f"ERROR:{ln}: id must contain at least one ':' to form path, got '{jid}'", file=sys.stderr)
                errors += 1
                continue

            # last part is filename, others are directories
            *dirs, filename = parts
            out_dir = out_root.joinpath(*dirs)
            out_file = out_dir / f"{filename}.json"

            if out_file.exists() and not args.overwrite:
                print(f"ERROR:{ln}: exists and --overwrite not set: {out_file}", file=sys.stderr)
                errors += 1
                continue

            # pretty JSON with stable key order
            data = (json.dumps(obj, ensure_ascii=False, indent=args.indent, sort_keys=False) + "\n").encode("utf-8")

            if args.dry_run:
                print(f"[DRY] write -> {out_file}")
            else:
                out_dir.mkdir(parents=True, exist_ok=True)
                with open(out_file, "wb") as wf:
                    wf.write(data)
                outputs.append(out_file)

    if errors:
        print(f"\nCompleted with {errors} error(s). Fix and rerun.", file=sys.stderr)
        if not args.dry_run:
            # do not write manifests if we had errors
            sys.exit(1)

    # Manifests
    if not args.dry_run:
        man_dir = out_root / "_manifests"
        man_dir.mkdir(parents=True, exist_ok=True)
        outputs_txt = man_dir / "outputs.txt"
        checksums = man_dir / "checksums.sha256"

        # Sort for determinism
        outputs = sorted(set(outputs), key=lambda p: str(p))

        with outputs_txt.open("w", encoding="utf-8") as mf:
            for p in outputs:
                mf.write(str(p.relative_to(out_root)) + "\n")

        # Compute SHA256 for each written file
        with checksums.open("w", encoding="utf-8") as cf:
            for p in outputs:
                with open(p, "rb") as rf:
                    h = sha256_bytes(rf.read())
                rel = str(p.relative_to(out_root))
                cf.write(f"{h}  {rel}\n")

        print(f"Wrote {len(outputs)} files.")
        print(f"Manifest: {outputs_txt}")
        print(f"Checksums: {checksums}")

if __name__ == "__main__":
    main()
