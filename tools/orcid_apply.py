# tools/orcid_apply.py
#!/usr/bin/env python3
"""
ORCID Apply — writes vetted ORCIDs into authors.master.yaml

What this does
--------------
Reads an approvals CSV (usually citations/_manifests/orcid_approved.csv) and
applies the selected ORCID iDs to matching authors in your master YAML.

Inputs
------
- ENV AUTH_MASTER (optional): path to the master YAML.
  Defaults to "citations/authors.master.yaml".
- CLI arg <approved_review.csv>: a CSV with columns including:
  - author_id (required)
  - approve (expected "y"/"yes"/"true"/"1")
  - chosen_orcid (preferred) or orcid (fallback)

Outputs
-------
- Updates the master YAML in place (with a safety backup by default).
- Prints a concise summary (updated, skipped, invalid, missing).

Typical usage
-------------
python3 tools/orcid_apply.py citations/_manifests/orcid_approved.csv

Options
-------
--force     : overwrite an existing non-empty ORCID in master (default: only fill if empty).
--no-backup : do not write a *.bak copy of the master before modifying.

Idempotence & safety
--------------------
- Re-running is safe: only approved rows are considered; unchanged values are skipped.
- By default, existing non-empty ORCIDs are NOT overwritten unless --force is used.

"""

import os
import re
import sys
import csv
import shutil
import pathlib
import yaml
from typing import Dict, Any

# --- Config / Paths ---
AUTH_MASTER_PATH = os.environ.get("AUTH_MASTER", "citations/authors.master.yaml")
AUTH_MASTER = pathlib.Path(AUTH_MASTER_PATH)

ORCID_RE = re.compile(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$')


def valid_orcid(s: str) -> bool:
    return bool(ORCID_RE.match((s or "").strip()))


def load_master(p: pathlib.Path) -> Dict[str, Any]:
    if not p.exists():
        print(f"ERROR: master not found: {p}", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(p.read_text())


def save_master(p: pathlib.Path, data: Dict[str, Any], backup: bool = True) -> None:
    if backup:
        bk = p.with_suffix(p.suffix + ".bak")
        shutil.copy2(p, bk)
        print(f"🧷 Backup → {bk}")
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def parse_args():
    import argparse
    ap = argparse.ArgumentParser(
        description="Apply approved ORCID iDs to authors.master.yaml",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("approved_csv", help="Path to orcid_approved.csv (or any approvals CSV)")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing non-empty ORCIDs in master")
    ap.add_argument("--no-backup", action="store_true",
                    help="Do not write a .bak copy of the master file")
    return ap.parse_args()


def main():
    args = parse_args()

    approved_csv = pathlib.Path(args.approved_csv)
    if not approved_csv.exists():
        print(f"ERROR: file not found: {approved_csv}", file=sys.stderr)
        return 2

    print(f"📘 Using author master: {AUTH_MASTER}")

    data = load_master(AUTH_MASTER)
    authors_list = data.get("authors", [])
    authors_by_id = {a.get("id"): a for a in authors_list}

    updated = 0
    skipped_same = 0
    skipped_present = 0
    invalid = 0
    missing = 0
    considered = 0

    with approved_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            considered += 1

            # Only process explicit approvals
            approve = (row.get("approve") or "").strip().lower()
            if approve not in ("y", "yes", "true", "1"):
                continue

            aid = (row.get("author_id") or "").strip()
            if not aid:
                invalid += 1
                continue

            orcid = (row.get("chosen_orcid") or row.get("orcid") or "").strip()
            if not valid_orcid(orcid):
                invalid += 1
                continue

            a = authors_by_id.get(aid)
            if not a:
                missing += 1
                continue

            current = (a.get("orcid") or "").strip()

            # If already the same, skip
            if current == orcid:
                skipped_same += 1
                continue

            # If already set to something else, only overwrite with --force
            if current and not args.force:
                skipped_present += 1
                continue

            # Apply
            a["orcid"] = orcid
            updated += 1

    # Write master back
    save_master(AUTH_MASTER, data, backup=(not args.no_backup))

    print(
        "✅ ORCID apply summary:\n"
        f"   considered rows : {considered}\n"
        f"   updated          : {updated}\n"
        f"   skipped (same)   : {skipped_same}\n"
        f"   skipped (present): {skipped_present}  (use --force to overwrite)\n"
        f"   invalid rows     : {invalid}\n"
        f"   missing authors  : {missing}\n"
        f"→ Wrote: {AUTH_MASTER}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())