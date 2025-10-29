# 🧾 Authors Directory — LSDMU Bibliography

This folder contains **split author YAML files** generated from the canonical registry  
[`citations/authors.master.yaml`](../authors.master.yaml).

Each file represents a **single unique author, editor, or historical figure** cited in  
Christopher M. Bache’s *LSD and the Mind of the Universe* (2019).

---

## 📘 Purpose

This directory provides a **normalized, machine-readable registry** of all individuals referenced in the LSDMU bibliography.  
It serves as the *Author Layer* in the Bache Graph:

Text Segment → Work → Author

Together, these layers form the influence map of Bache’s work within the broader  
**Lumen Graph** of evolutionary mysticism, consciousness studies, and transpersonal research.

---

## 🧩 Structure

Each file follows this format:

```yaml
id: grof-stanislav
entity_type: person
full_name: Stanislav Grof
family: Grof
given: Stanislav
lifespan: 1931–2024
nationality: Czech-American
fields: [psychiatry, transpersonal psychology]
wikidata: Q76122
orcid: null
aliases:
  variants: [Grof, S.]
  misspellings: []
notable_works: [grof-1980-lsd-psychotherapy, grof-1976-realms]
notes: Author of *LSD Psychotherapy* and key influence on Bache’s methodology.
review_state: draft
curator: bibliography-team
created_at: 2025-10-29

Field Order (Canonical)

id, entity_type, full_name, family, given, lifespan, nationality,
fields, wikidata, orcid, aliases, notable_works, notes,
review_state, curator, created_at

All indentation is 2 spaces, lists are in inline YAML form, and ASCII-safe ids
follow the convention family-given[-middle].

⸻

⚙️ Regeneration Workflow

These files are not edited manually.
They are generated automatically from the master YAML via the tools below.

Step 1 — Validate the Master

tools/authors_validate.py --master citations/authors.master.yaml

Step 2 — Regenerate Splits

tools/authors_split.py --master citations/authors.master.yaml --outdir citations/authors --clean

This will:
	•	Validate schema compliance
	•	Remove any old .yaml files
	•	Recreate one clean file per author
	•	Preserve .gitkeep to keep this directory tracked

⸻

🧰 Related Tools

Script	Description
tools/authors_validate.py	Checks field order, duplicates, and required keys
tools/authors_split.py	Regenerates one YAML per author from the master file


⸻

🗂️ Versioning & Backups
	•	Backups of previous author files are stored in _backups/ (excluded via .gitignore).
	•	Commits should only include regenerated files and updates to authors.master.yaml.
	•	Each new author should be added only to the master file — never directly here.

⸻

✅ Status

✔ All 100+ authors validated and regenerated
✔ Schema conforms to LSDMU Author Mastering v1.1
✔ Directory clean and reproducible

⸻

🧠 Maintainers

Bibliography Team — Bache Archive Stewardship Project
Curators: bibliography-team
Created: 2025-10-29

⸻

“Every author is a node in the web of awakening.
This registry ensures none are lost to time.”
