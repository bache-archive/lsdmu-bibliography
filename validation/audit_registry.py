import json, csv
from pathlib import Path
from collections import Counter

REG = Path("citations/registry")
VALDIR = Path("validation")
VALDIR.mkdir(exist_ok=True, parents=True)

def year_of(d):
    try:
        return d["issued"]["date-parts"][0][0]
    except Exception:
        return None

by_type = Counter()
by_decade = Counter()
by_topic = Counter()
errors = []
files = sorted(p for p in REG.glob("*.json"))

for p in files:
    try:
        d = json.loads(p.read_text())
    except Exception as e:
        errors.append((p.name, f"JSON parse error: {e}"))
        continue

    _id = d.get("id")
    if not _id:
        errors.append((p.name, "missing id"))
    elif _id != p.stem:
        errors.append((p.name, f"id != filename stem ('{_id}' vs '{p.stem}')"))

    typ = d.get("type","(missing)")
    by_type[typ] += 1

    y = year_of(d)
    dec = f"{(y//10)*10}s" if isinstance(y,int) else "unknown"
    by_decade[dec] += 1

    for t in d.get("topics", []):
        by_topic[t] += 1

md = []
md.append("# Registry Audit Report\n")
md.append(f"- Files scanned: **{len(files)}**\n")

md.append("## By Type")
for k,v in sorted(by_type.items()):
    md.append(f"- {k}: {v}")

md.append("\n## By Decade (issued year)")
for k,v in sorted(by_decade.items()):
    md.append(f"- {k}: {v}")

md.append("\n## Top Topics (first 40)")
for k,v in sorted(by_topic.items(), key=lambda kv: kv[1], reverse=True)[:40]:
    md.append(f"- {k}: {v}")

if errors:
    md.append("\n## Errors / Warnings")
    for fn,msg in errors[:200]:
        md.append(f"- {fn}: {msg}")
    if len(errors) > 200:
        md.append(f"- ... and {len(errors)-200} more")

(VALDIR/"registry_audit_report.md").write_text("\n".join(md))

with open(VALDIR/"registry_audit.csv","w",newline="") as f:
    w = csv.writer(f)
    w.writerow(["filename","type","year","topics_count"])
    for p in files:
        try:
            d = json.loads(p.read_text())
            y = year_of(d)
            w.writerow([p.name, d.get("type",""), y if y is not None else "", len(d.get("topics",[]))])
        except Exception:
            w.writerow([p.name, "ERROR", "", 0])

print("Wrote validation/registry_audit_report.md and validation/registry_audit.csv")
