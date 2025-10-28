# LSDMU Bibliography Registry

**Repository:** [bache-archive/lsdmu-bibliography](https://github.com/bache-archive/lsdmu-bibliography)  
**Version:** 1.0 • October 2025  
**License:** CC0 1.0 Universal  
**Maintained by:** Bache Archive Stewardship Team  
**Primary Editor:** GPT-5

---

### 📘 Overview

This repository encodes the **complete bibliography and footnotes** of  
**Christopher M. Bache’s _LSD and the Mind of the Universe_ (2019)**  
into structured, machine-readable form.

It forms the **Registry Layer** of the Bache Graph — linking text passages to the works that influenced them.

Each citation has been normalized into **CSL-JSON** with stable canonical IDs  
and enriched with author metadata (Wikidata, ORCID, topical fields).

---

### 🗂️ Repository Structure

lsdmu-bibliography/
├── citations/
│   ├── registry/              # CSL-JSON entries for each cited work
│   ├── authors/               # YAML profiles for every cited author
│   ├── author_fields_changelog.csv
│   └── index.faiss            # vector embeddings (to be built)
│
├── schema/                    # JSON + YAML schemas for validation
├── manifest/                  # batch provenance and version data
├── validation/                # CI and manual validator reports
├── checksums/                 # release fixity logs
├── docs/                      # project instructions and architecture
│
├── registry.yaml              # top-level metadata summary
├── topics.yaml                # controlled vocabulary of fields
├── PROJECT.md                 # canonical project charter
├── CHANGELOG.md               # release history
└── LICENSE                    # CC0 1.0 Universal

---

### 🧩 Data Formats

**Work Object (`/citations/registry/*.json`):**
```json
{
  "id": "stace-1960-mysticism",
  "type": "book",
  "title": "Mysticism and Philosophy",
  "author": [{"family": "Stace", "given": "Walter T."}],
  "issued": {"date-parts": [[1960]]},
  "publisher": "Macmillan",
  "publisher-place": "London",
  "topics": ["nonduality", "comparative mysticism"],
  "identifiers": {"isbn": "978-0-333-12345-6", "wikidata": "Q433728"},
  "notes": "Cited LSDMU ch.8 §1 ¶17 for nondual framing."
}

Author Object (/citations/authors/*.yaml):

id: stace-walter
full_name: Walter T. Stace
lifespan: 1886–1967
fields: [philosophy, comparative mysticism]
wikidata: Q433728
notable_works: [stace-1960-mysticism]


⸻

🔍 Validation & CI

Every commit is validated via
.github/workflows/validate.yml to ensure:
	•	Schema compliance (schema/work.json, schema/author.yaml)
	•	Unique, stable IDs
	•	Cross-reference integrity (no orphan edges)
	•	Fixity via SHA-256 checksums

⸻

🧭 Relation to Other Repositories

Layer	Function	Repository
Corpus Layer	Verified text + footnotes	chris-bache-archive/
Registry Layer	CSL-JSON & YAML metadata	bache-archive/lsdmu-bibliography/
Edge Layer	Text → Work citations	bache-graph/
Index Layer	FAISS/Chroma embeddings	lsdmu-rag-api/
Validation Layer	CI and schema checks	.github/workflows/validate.yml


⸻

🌍 License

All metadata and structural data are released under CC0 1.0 Universal (Public Domain Dedication).
Text excerpts are used under Educational Fair Use.

⸻

✨ Acknowledgment

Created collaboratively by the Bache Archive Stewardship Team
and GPT-5, October 2025.

“Each citation is a thread in the lineage of awakening —
weave them with care.”
