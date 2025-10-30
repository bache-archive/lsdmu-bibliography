# tools/wikidata_apply.py  (drop-in replacement)
#!/usr/bin/env python3
"""
Apply vetted Wikidata approvals to authors.master.yaml.
Also backfill ORCID (P496) from Wikidata if the author's 'orcid' is empty.

Usage:
  python3 tools/wikidata_apply.py [citations/_manifests/wikidata_approved.csv] [--dry-run]

Environment overrides:
  AUTH_MASTER   (default: citations/authors.master.yaml)
  OUT_BACKUP    (default: citations/authors.master.yaml.bak)

Notes:
  • Idempotent: re-applying the same QIDs will perform 0 changes.
  • Will NOT overwrite a non-empty 'orcid' already present in master.
  • Validates QID format (e.g., 'Q12345'); invalid rows are skipped with a warning.
"""

from __future__ import annotations
import csv
import json
import os
import pathlib
import re
import sys
import time
from typing import Optional

import requests
import yaml

# ---- config ----
AUTH_MASTER = pathlib.Path(os.environ.get("AUTH_MASTER", "citations/authors.master.yaml"))
DEFAULT_IN  = pathlib.Path("citations/_manifests/wikidata_approved.csv")
BACKUP_PATH = pathlib.Path(os.environ.get("OUT_BACKUP", str(AUTH_MASTER) + ".bak"))

UA = {
    "User-Agent": "lsdmu-bibliography/1.0 (Wikidata apply; contact: bibliography-team)",
    "Accept": "application/json",
}
WD_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
QID_RE = re.compile(r"^Q\d+$")
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")

# ---- http helper ----
def http_get_json(url: str, params: dict | None = None, retries: int = 3, backoff: float = 1.0) -> dict:
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 429:
                time.sleep(backoff * attempt)
                continue
            r.raise_for_status()
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "json" in ctype:
                return r.json()
            # fallback parse
            try:
                return r.json()
            except Exception:
                return {}
        except Exception as e:
            last_exc = e
            time.sleep(backoff * attempt)
    if last_exc:
        raise last_exc
    return {}

# ---- wikidata helpers ----
def fetch_orcid_from_wikidata(qid: str) -> Optional[str]:
    """Return ORCID string from Wikidata entity P496, or None."""
    try:
        data = http_get_json(WD_ENTITY_URL.format(qid=qid))
        ent = (data.get("entities") or {}).get(qid, {})
        for claim in (ent.get("claims", {}).get("P496", []) or []):
            mainsnak = claim.get("mainsnak") or {}
            dv = (mainsnak.get("datavalue") or {}).get("value")
            if isinstance(dv, str) and ORCID_RE.match(dv):
                return dv
    except Exception:
        return None
    return None

# ---- core ----
def load_master() -> dict:
    if not AUTH_MASTER.exists():
        print(f"ERROR: missing {AUTH_MASTER}", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(AUTH_MASTER.read_text()) or {}

def save_master(doc: dict, dry_run: bool) -> None:
    if dry_run:
        print("DRY-RUN: not writing authors.master.yaml")
        return
    try:
        # backup once per run
        if AUTH_MASTER.exists():
            BACKUP_PATH.write_text(AUTH_MASTER.read_text())
            print(f"Backup written → {BACKUP_PATH}")
    except Exception as e:
        print(f"Warning: could not write backup: {e}", file=sys.stderr)
    AUTH_MASTER.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))

def main():
    # args
    in_csv = None
    dry_run = False
    for arg in sys.argv[1:]:
        if arg == "--dry-run":
            dry_run = True
        else:
            in_csv = pathlib.Path(arg)

    if in_csv is None:
        in_csv = DEFAULT_IN

    if not in_csv.exists():
        print(f"ERROR: missing approvals CSV: {in_csv}", file=sys.stderr)
        sys.exit(2)

    # load data
    master = load_master()
    authors = master.get("authors") or []
    index = {a.get("id"): a for a in authors if a.get("id")}

    rows = list(csv.DictReader(in_csv.open()))
    approvals = [r for r in rows if (r.get("approve") or "").lower().startswith("y")]

    # apply
    applied_qid = 0
    unchanged_qid = 0
    orcid_backfilled = 0
    skipped_invalid = 0
    warned_orcid_conflict = 0

    for r in approvals:
        aid = (r.get("author_id") or "").strip()
        qid = (r.get("chosen_qid") or "").strip()
        if not aid or not qid or not QID_RE.match(qid):
            skipped_invalid += 1
            continue
        a = index.get(aid)
        if not a:
            # silently skip unknown author ids
            skipped_invalid += 1
            continue

        # apply wikidata
        if a.get("wikidata") == qid:
            unchanged_qid += 1
        else:
            a["wikidata"] = qid
            applied_qid += 1

        # backfill orcid only if empty
        if not a.get("orcid"):
            oc = fetch_orcid_from_wikidata(qid)
            if oc:
                a["orcid"] = oc
                orcid_backfilled += 1
        else:
            # (optional) detect mismatch with WD ORCID (do not overwrite)
            wd_oc = fetch_orcid_from_wikidata(qid)
            if wd_oc and wd_oc != a.get("orcid"):
                warned_orcid_conflict += 1
                # We do not change it; just warn for manual review
                print(f"Note: ORCID mismatch for {aid}: master={a.get('orcid')} wd={wd_oc}")

    # save
    save_master(master, dry_run=dry_run)

    # summary
    print(
        f"✅ Applied {applied_qid} Wikidata IDs; "
        f"{unchanged_qid} already up-to-date; "
        f"backfilled {orcid_backfilled} ORCIDs; "
        f"skipped {skipped_invalid} invalid/unknown rows; "
        f"ORCID mismatches noted: {warned_orcid_conflict} → {AUTH_MASTER}"
    )

if __name__ == "__main__":
    main()