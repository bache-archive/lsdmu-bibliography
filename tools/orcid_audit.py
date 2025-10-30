# tools/orcid_audit.py
# Purpose: audit ORCID IDs in citations/authors.master.yaml
# Adds progress output while running for large author lists.

import os, re, sys, csv, json, time, pathlib, datetime, urllib.request, yaml

ENV_PATH = os.environ.get("AUTH_MASTER", "citations/authors.master.yaml")
AUTH_MASTER = pathlib.Path(ENV_PATH)
OUT = pathlib.Path("citations/_manifests/orcid_audit.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$")
TODAY = datetime.date.today().isoformat()

def iso7064_check(orcid):
    digits = orcid.replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    remainder = total % 11
    result = (12 - remainder) % 11
    check = "X" if result == 10 else str(result)
    return check == digits[-1]

def http_json(url, hdrs=None, timeout=20):
    req = urllib.request.Request(url, headers=hdrs or {"Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8")), r.getcode()

def soft_norm_name(s): return re.sub(r"[^a-z]", "", (s or "").lower())

def name_match_score(author_full, orcid_record):
    try:
        names = orcid_record["person"]["name"]
        given = names.get("given-names", {}).get("value") or ""
        family = names.get("family-name", {}).get("value") or ""
    except Exception:
        given = family = ""
    target = soft_norm_name(author_full)
    a = soft_norm_name(f"{given} {family}")
    b = soft_norm_name(f"{family} {given}")
    score = 0
    if a and a == target: score = 100
    elif b and b == target: score = 98
    alias_hit = False
    try:
        also = orcid_record["person"].get("other-names", {}).get("other-name", []) or []
        for n in also:
            if soft_norm_name(n.get("content","")) == target:
                alias_hit = True; break
    except Exception:
        pass
    if score == 0:
        if given and family and soft_norm_name(family) in target and target.startswith(soft_norm_name(given[:1])):
            score = 85
        elif alias_hit:
            score = 80
        elif given and family and soft_norm_name(family) in target and soft_norm_name(given[:2]) in target:
            score = 70
    return score, given, family, alias_hit

def orcid_exists(orcid):
    url = f"https://pub.orcid.org/v3.0/{orcid}"
    try:
        data, code = http_json(url, {"Accept":"application/json"})
        return True, data
    except urllib.error.HTTPError as e:
        if e.code == 404: return False, None
        raise
    except Exception:
        return None, None

def wd_p496_for_qid(qid):
    if not qid: return []
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    try:
        data, _ = http_json(url)
        ent = data["entities"][qid]
        vals = []
        for c in ent.get("claims", {}).get("P496", []):
            m = c.get("mainsnak", {})
            if m.get("snaktype") == "value" and "datavalue" in m:
                vals.append(m["datavalue"]["value"])
        return list(set(vals))
    except Exception:
        return []

def load_master():
    text = AUTH_MASTER.read_text(encoding="utf-8")
    items = []
    try:
        for doc in yaml.safe_load_all(text):
            if doc is None: continue
            if isinstance(doc, list):
                items.extend([x for x in doc if isinstance(x, dict)])
            elif isinstance(doc, dict):
                if "authors" in doc and isinstance(doc["authors"], list):
                    items.extend([x for x in doc["authors"] if isinstance(x, dict)])
                else:
                    items.append(doc)
        if items: return items
    except Exception:
        pass
    data = yaml.safe_load(text)
    if isinstance(data, list): return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict): return [data]
    return []

def main():
    authors = load_master()
    if not authors:
        print(f"ERROR: No author records parsed from {AUTH_MASTER}", file=sys.stderr)
        sys.exit(1)

    rows = []
    bad_format = nonexistent = mismatch = ok = manual = 0
    total = len(authors)
    print(f"🔍 Auditing {total} authors...")

    for i, a in enumerate(authors, 1):
        if not isinstance(a, dict): continue
        aid = a.get("id")
        name = a.get("full_name")
        orcid = (a.get("orcid") or "").strip() or None
        qid = a.get("wikidata") or None

        if i % 10 == 0:
            print(f"  • Checked {i}/{total} ({int(i/total*100)}%)...")

        if not orcid:
            rows.append([aid, name, "", "no_orcid", "", "", "", "", "", qid, ""])
            continue

        fmt_ok = bool(ORCID_RE.match(orcid)) and iso7064_check(orcid)
        if not fmt_ok:
            rows.append([aid, name, orcid, "bad_format", "", "", "", "", "", qid, "drop"])
            bad_format += 1
            continue

        exists, rec = orcid_exists(orcid)
        if exists is False:
            rows.append([aid, name, orcid, "not_found_404", "", "", "", "", "", qid, "drop"])
            nonexistent += 1
            continue
        elif exists is None:
            rows.append([aid, name, orcid, "network_error", "", "", "", "", "", qid, "manual"])
            manual += 1
            continue

        score, given, family, alias_hit = name_match_score(name, rec)
        wd_vals = wd_p496_for_qid(qid)
        wd_match = "y" if (orcid and orcid in wd_vals) else ("n" if wd_vals else "")

        decision = "keep" if score >= 85 else ("manual" if 70 <= score < 85 else "drop")
        if wd_match == "y" and decision == "drop":
            decision = "manual"

        status = "ok" if decision == "keep" else ("review" if decision == "manual" else "mismatch")
        if status == "ok": ok += 1
        elif status == "mismatch": mismatch += 1
        else: manual += 1

        rows.append([
            aid, name, orcid, status, score, given, family,
            "alias_hit" if alias_hit else "",
            wd_match, qid or "", decision
        ])
        time.sleep(0.15)

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "author_id","full_name","orcid","status","name_match_score",
            "orcid_given","orcid_family","alias_flag",
            "wikidata_p496_match","wikidata_qid","decision"
        ])
        w.writerows(rows)

    print(f"\n✅ wrote {OUT}")
    print(f"   ok={ok}, bad_format={bad_format}, not_found={nonexistent}, mismatch={mismatch}, manual={manual}")

if __name__ == "__main__":
    main()