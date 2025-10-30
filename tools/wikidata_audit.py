#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv, os, re, sys, time, requests, yaml
from collections import defaultdict

AUTH_MASTER = os.environ.get("AUTH_MASTER", "citations/authors.master.yaml")
OUT_CSV = "citations/_manifests/wikidata_audit.csv"
WD_API = "https://www.wikidata.org/w/api.php"

# ---- config: be polite to WD API
CONTACT = os.environ.get("WD_CONTACT", "elias.m.hart@proton.me")  # set to your contact
USER_AGENT = f"LSDMU-WD-Audit/1.0 ({CONTACT})"
CHUNK = int(os.environ.get("WD_CHUNK", "25"))
SLEEP_BETWEEN = float(os.environ.get("WD_SLEEP", "0.4"))
RETRIES = 4
BACKOFF = 2.0

sess = requests.Session()
sess.headers.update({"User-Agent": USER_AGENT})

def slug(s): return re.sub(r"[^a-z0-9]+","",(s or "").lower())

def name_score(local_name, wd_label, wd_aliases):
    ln = (local_name or "").strip()
    if not ln: return 0
    ln_norm = slug(ln); lab_norm = slug(wd_label or "")
    alias_norms = {slug(a) for a in (wd_aliases or [])}
    if ln_norm and ln_norm == lab_norm: return 100
    if ln_norm in alias_norms: return 95
    parts = ln.split()
    if len(parts) >= 2:
        fam = slug(parts[-1]); init = "".join(p[0].lower() for p in parts[:-1] if p)
        lab_parts = (wd_label or "").split()
        if len(lab_parts) >= 2:
            lab_fam = slug(lab_parts[-1]); lab_init = "".join(p[0].lower() for p in lab_parts[:-1] if p)
            if fam and fam==lab_fam and init and init==lab_init: return 90
    if ln_norm and wd_label and (parts[-1].lower() in wd_label.lower()): return 70
    return 0

def get_p_values(claims, pid):
    vals = []
    for c in claims.get(pid, []):
        snak = c.get("mainsnak", {})
        if snak.get("snaktype") != "value": continue
        dv = snak.get("datavalue", {})
        t = dv.get("type")
        if t == "wikibase-entityid":
            vals.append("Q" + str(dv["value"]["numeric-id"]))
        elif t == "string":
            vals.append(dv["value"])
    return vals

def load_authors(path):
    data = yaml.safe_load(open(path, "r", encoding="utf-8"))
    if isinstance(data, dict) and "authors" in data: return data["authors"]
    if isinstance(data, list): return data
    return []

def wbgetentities(qids):
    params = {
        "action": "wbgetentities",
        "format": "json",
        "formatversion": "2",
        "ids": "|".join(qids),
        "props": "labels|aliases|claims|descriptions",
        "languages": "en",
        "maxlag": "5",
    }
    attempt = 0
    while True:
        attempt += 1
        r = sess.get(WD_API, params=params, timeout=30)
        if r.status_code == 200:
            j = r.json()
            # handle maxlag/server lag gracefully
            if "error" in j and j["error"].get("code") == "maxlag":
                time.sleep(BACKOFF ** attempt)
                continue
            return j.get("entities", {})
        if r.status_code in (429, 403, 502, 503):
            time.sleep(BACKOFF ** attempt)
            if attempt <= RETRIES: continue
        r.raise_for_status()

def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "author_id","full_name","wikidata_qid","wd_label","name_match_score",
            "is_human","wd_alias_hit","local_orcid","wd_orcids","orcid_status",
            "decision","notes"
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)

def main():
    authors = load_authors(AUTH_MASTER)
    rows = []
    qids, index = [], []
    for a in authors:
        if not isinstance(a, dict): continue
        aid = a.get("id")
        qid = str(a.get("wikidata") or "").strip()
        if aid and re.match(r"^Q\d+$", qid):
            qids.append(qid); index.append((aid, a))

    total = len(qids)
    print(f"🔎 Auditing {total} Wikidata items...")

    for i in range(0, total, CHUNK):
        chunk = qids[i:i+CHUNK]
        entities = wbgetentities(chunk)
        pct = min(100, int((i+len(chunk))*100/total)) if total else 100
        print(f"  • Checked {i+len(chunk)}/{total} ({pct}%)...")

        for q, (aid, a) in zip(chunk, index[i:i+CHUNK]):
            local_name = a.get("full_name") or ""
            local_orcid = (a.get("orcid") or "").strip()
            ent = entities.get(q, {}) or {}
            labels = ent.get("labels", {})
            lab_en = labels.get("en", {}).get("value") if isinstance(labels.get("en"), dict) else labels.get("en")
            alias_en = []
            aliases = ent.get("aliases", {})
            if isinstance(aliases.get("en"), list):
                alias_en = [al.get("value") for al in aliases["en"] if isinstance(al, dict) and "value" in al]

            claims = ent.get("claims", {}) or {}
            p31 = set(get_p_values(claims, "P31"))
            p496s = get_p_values(claims, "P496")

            score = name_score(local_name, lab_en, alias_en)
            is_human = "Q5" in p31

            if local_orcid and p496s:
                orcid_status = "ok" if local_orcid in p496s else "mismatch"
            elif local_orcid and not p496s:
                orcid_status = "local_only"
            elif not local_orcid and p496s:
                orcid_status = "wikidata_only"
            else:
                orcid_status = "none"

            decision, notes = "keep", []
            if not is_human:
                decision = "review"; notes.append("not_human")
            if score >= 90:
                pass
            elif score >= 70:
                decision = "manual"; notes.append("name_loose")
            else:
                decision = "review"; notes.append("name_mismatch")
            if orcid_status == "mismatch":
                decision = "review"; notes.append("orcid_mismatch")

            rows.append({
                "author_id": aid,
                "full_name": local_name,
                "wikidata_qid": q,
                "wd_label": lab_en or "",
                "name_match_score": score,
                "is_human": "y" if is_human else "n",
                "wd_alias_hit": "y" if (score >= 95 and lab_en != local_name) else "",
                "local_orcid": local_orcid,
                "wd_orcids": ";".join(p496s),
                "orcid_status": orcid_status,
                "decision": decision,
                "notes": ";".join(notes) if notes else ""
            })

        # write progress every chunk
        write_csv(OUT_CSV, rows)
        time.sleep(SLEEP_BETWEEN)

    # final summary
    counts = defaultdict(int)
    for r in rows: counts[r["decision"]] += 1
    print(f"✅ wrote {OUT_CSV}  (keep={counts['keep']}, manual={counts['manual']}, review={counts['review']})")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)