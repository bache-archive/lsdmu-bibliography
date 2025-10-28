import json, random
from pathlib import Path

REG = Path("citations/registry")
VALDIR = Path("validation")
VALDIR.mkdir(exist_ok=True, parents=True)

def decade(y): return f"{(y//10)*10}s" if isinstance(y,int) else "unknown"
def year(d):
    try: return d["issued"]["date-parts"][0][0]
    except: return None

bins = {}
for p in REG.glob("*.json"):
    try:
        d = json.loads(p.read_text())
    except:
        continue
    y = year(d)
    t = d.get("type","unknown")
    k = (t, decade(y))
    bins.setdefault(k, []).append(p.name)

out = []
random.seed(37)
for k, items in sorted(bins.items()):
    out.extend(random.sample(items, min(2, len(items))))  # up to 2 from each bin

(VALDIR/"sample_list.txt").write_text("\n".join(out))
print("Wrote validation/sample_list.txt with", len(out), "files")
