# tools/wikidata_apply.py
#!/usr/bin/env python3
"""
Apply vetted Wikidata approvals to authors.master.yaml.
Also backfill ORCID from Wikidata entity (P496) if orcid is null.

Usage:
  python3 tools/wikidata_apply.py citations/_manifests/wikidata_approved.csv
"""
import sys, csv, pathlib, yaml, json, time, requests, re

AUTH_MASTER = pathlib.Path("citations/authors.master.yaml")
UA = {"User-Agent":"lsdmu-bibliography/1.0 (Wikidata apply; contact: bibliography-team)",
      "Accept":"application/json"}
WD_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

def http_get(url, params=None):
    for attempt in range(3):
        r = requests.get(url, params=params, headers=UA, timeout=30)
        if r.status_code == 429:
            time.sleep(1.0*(attempt+1)); continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("HTTP retries exhausted")

def fetch_orcid_from_wd(qid: str):
    try:
        data = http_get(WD_ENTITY.format(qid=qid))
        ent = (data.get("entities") or {}).get(qid, {})
        claims = ent.get("claims", {})
        for c in claims.get("P496", []):
            v = c["mainsnak"]["datavalue"]["value"]
            if re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$', v):
                return v
    except Exception:
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: wikidata_apply.py citations/_manifests/wikidata_approved.csv")
        sys.exit(2)
    approved_csv = pathlib.Path(sys.argv[1])
    app_rows = [r for r in csv.DictReader(approved_csv.open()) if (r.get("approve") or "").lower().startswith("y")]
    d = yaml.safe_load(AUTH_MASTER.read_text())
    ix = {a["id"]: a for a in d["authors"]}
    updates = 0
    orcid_filled = 0

    for r in app_rows:
        aid = r["author_id"]; qid = r["chosen_qid"]
        a = ix.get(aid)
        if not a: continue
        if a.get("wikidata") != qid:
            a["wikidata"] = qid
            updates += 1
        if not a.get("orcid"):
            oc = fetch_orcid_from_wd(qid)
            if oc:
                a["orcid"] = oc
                orcid_filled += 1

    # write back preserving order
    AUTH_MASTER.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    print(f"✅ Applied {updates} Wikidata IDs; backfilled {orcid_filled} ORCIDs → {AUTH_MASTER}")

if __name__ == "__main__":
    main()
