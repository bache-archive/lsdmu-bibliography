# tools/enrichment_summary.py
#!/usr/bin/env python3
import csv, pathlib, yaml

MASTER = pathlib.Path("citations/authors.master.yaml")
OUT = pathlib.Path("citations/_manifests/enrichment_summary.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

def as_join(x):
    if not x: return ""
    return "; ".join(str(v) for v in x)

def main():
    data = yaml.safe_load(MASTER.read_text())
    authors = data.get("authors", [])
    rows = []
    for a in authors:
        aid = a.get("id","")
        rows.append({
            "id": aid,
            "full_name": a.get("full_name",""),
            "orcid": a.get("orcid",""),
            "wikidata": a.get("wikidata",""),
            "has_orcid": "y" if a.get("orcid") else "",
            "has_wikidata": "y" if a.get("wikidata") else "",
            "lifespan": a.get("lifespan",""),
            "nationality": a.get("nationality",""),
            "fields": as_join(a.get("fields")),
            "notable_works": as_join(a.get("notable_works")),
            "review_state": a.get("review_state",""),
        })

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    have_orcid = sum(1 for r in rows if r["has_orcid"])
    have_wd = sum(1 for r in rows if r["has_wikidata"])
    print(f"✅ wrote {OUT}  (authors={len(rows)}, with_orcid={have_orcid}, with_wikidata={have_wd})")

if __name__ == "__main__":
    main()
