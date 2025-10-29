# tools/orcid_apply.py
#!/usr/bin/env python3
import csv, pathlib, yaml, sys, re

AUTH_MASTER = pathlib.Path("citations/authors.master.yaml")

def valid_orcid(s):
    return bool(re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$', s or ""))

def main():
    if len(sys.argv) < 2:
        print("Usage: tools/orcid_apply.py <approved_review.csv>", file=sys.stderr)
        return 2
    review = pathlib.Path(sys.argv[1])
    if not review.exists():
        print(f"ERROR: file not found: {review}", file=sys.stderr); return 2

    data = yaml.safe_load(AUTH_MASTER.read_text())
    authors = {a["id"]: a for a in data["authors"]}

    updates = 0
    with review.open() as f:
        r = csv.DictReader(f)
        for row in r:
            if (row.get("approve") or "").strip().lower() not in ("y","yes","true","1"):
                continue
            aid = (row.get("author_id") or "").strip()
            orcid = (row.get("chosen_orcid") or row.get("orcid") or "").strip()
            if not aid or not valid_orcid(orcid) or aid not in authors:
                continue
            if authors[aid].get("orcid") == orcid:
                continue
            authors[aid]["orcid"] = orcid
            updates += 1

    data["authors"] = list(authors.values())
    AUTH_MASTER.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    print(f"✅ Updated {updates} ORCIDs in {AUTH_MASTER}")

if __name__ == "__main__":
    sys.exit(main())
