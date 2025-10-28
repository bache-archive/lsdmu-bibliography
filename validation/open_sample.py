from pathlib import Path
p = Path("validation/sample_list.txt")
if not p.exists():
    raise SystemExit("Run `make sample` first.")
lines = [l.strip() for l in p.read_text().splitlines() if l.strip()]
sh = Path("validation/open_sample.sh")
sh.write_text("\n".join(f"cursor citations/registry/{l}" for l in lines) + "\n")
sh.chmod(0o755)
print("Wrote validation/open_sample.sh")
