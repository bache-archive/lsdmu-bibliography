# LSDMU Bibliography Registry

Repository: bache-archive/lsdmu-bibliography  
Version: 1.2 • October 2025  
License: CC0 1.0 Universal  
Maintained by: Bache Archive Project  
Primary Editor: GPT-5  

⸻

📘 Overview

This repository encodes the complete bibliography and footnotes of  
**Christopher M. Bache**’s *[LSD and the Mind of the Universe: Diamonds from Heaven](https://www.wikidata.org/wiki/Q136684740)* (2019)  
into structured, machine-readable form.

**Wikidata References**
- Author — [Christopher Martin Bache (Q112496741)](https://www.wikidata.org/wiki/Q112496741)  
- Work — [*LSD and the Mind of the Universe: Diamonds from Heaven* (Q136684740)](https://www.wikidata.org/wiki/Q136684740)

It forms the **Registry Layer** of the Bache Graph — linking text passages → works → authors.

Each citation is formatted as a single-line CSL-JSON record extended with a  
Bache Graph metadata block (`x-bache`), and each author is represented in a  
curated YAML author registry enriched with Wikidata, ORCID, and controlled topic fields.

⸻

🗂️ Repository Structure

lsdmu-bibliography/
├── citations/
│   ├── authors.master.yaml       # canonical source of all author records
│   ├── authors/                  # regenerated per-author YAMLs
│   ├── registry/                 # CSL-JSON works (one per cited item)
│   ├── registry.jsonl            # flattened list of all works (one JSON per line)
│   ├── _manifests/               # internal manifests for batch provenance
│   └── index.faiss               # vector index (to be built)
│
├── tools/
│   ├── authors_split.py          # rebuilds /authors/ from authors.master.yaml
│   └── authors_validate.py       # schema and duplication validator
│
├── schema/                       # JSON + YAML schemas for validation
├── manifest/                     # batch provenance and version data
├── validation/                   # CI and manual validator reports
├── checksums/                    # release fixity logs
├── docs/                         # project instructions and architecture
│
├── registry.yaml                 # top-level metadata summary
├── topics.yaml                   # controlled vocabulary of fields
├── PROJECT.md                    # canonical project charter
├── CHANGELOG.md                  # release history
└── LICENSE                       # CC0 1.0 Universal

⸻

🧩 Data Formats

**Work Object** (`/citations/registry/*.json` or `.jsonl`)

Each record follows CSL-JSON conventions with a Bache Graph extension block:

```json
{
  "id": "source:bache:LSDMU:bib:stace-1960-mysticism",
  "type": "book",
  "title": "Mysticism and Philosophy",
  "author": [{"family": "Stace", "given": "Walter T."}],
  "issued": {"date-parts": [[1960]]},
  "publisher": "Macmillan",
  "publisher-place": "London",
  "language": "en",
  "ISBN": "9780333123456",
  "x-bache": {
    "namespace": "bache",
    "citation_shorthand": "Stace 1960",
    "topics": ["nonduality", "comparative-mysticism"],
    "review_state": "steward-reviewed",
    "provenance": {
      "entered_by": "editor.hrl",
      "entered_at": "2025-10-28",
      "notes": "Validated against publisher record."
    },
    "mentioned_in": ["LSDMU.ch08.fn17"]
  }
}

Conventions
	•	One JSON object per line (.jsonl-ready).
	•	IDs follow: source:bache:LSDMU:bib:<slug>
	•	Fields normalized per CSL-JSON schema.
	•	All Bache-specific metadata lives inside x-bache.

⸻

Author Object (/citations/authors/*.yaml)

Each person or institutional author is represented once and linked by _author_ids.

id: stace-walter
entity_type: person
full_name: Walter Terence Stace
family: Stace
given: Walter T.
lifespan: 1886–1967
nationality: British
fields: [philosophy, comparative mysticism]
wikidata: Q433728
orcid: null
aliases:
  - Stace, Walter Terence
  - Stace, W. T.
notable_works:
  - stace-1960-mysticism
notes: >
  Frequently cited for nondual framing.
curator: hk-locke
created_at: 2025-10-29

All individual author files are regenerated automatically from
citations/authors.master.yaml, which is the single source of truth.

⸻

🔍 Validation & Build Workflow

Validation and build steps are automated in
.github/workflows/validate.yml and supported by the tools/ directory.

Checks include:
	•	✅ Schema compliance (schema/work.json, schema/author.yaml)
	•	✅ Unique, stable IDs
	•	✅ Cross-reference integrity (no orphan edges)
	•	✅ Author registry validation and split consistency
	•	✅ Fixity verification via SHA-256 checksums

You can regenerate authors or run validation anytime:

make authors-split
make authors-validate

⸻

🧭 Relation to Other Repositories

Layer	Function	Repository
Corpus Layer	Verified text + footnotes	chris-bache-archive￼
Registry Layer	CSL-JSON + YAML metadata	lsdmu-bibliography￼
Edge Layer	Text → Work citations	bache-graph￼
Index Layer	FAISS/Chroma embeddings	lsdmu-rag-api￼
Validation Layer	CI and schema checks	.github/workflows/validate.yml

⸻

🌍 License

All metadata and structural data are released under
CC0 1.0 Universal (Public Domain Dedication).
Text excerpts are used under Educational Fair Use.

⸻

✨ Acknowledgment

Created collaboratively by the Bache Archive Project and GPT-5, October 2025.

“Each citation is a thread in the lineage of awakening — weave them with care.”

⸻

🔄 Summary of Recent Updates
	•	v1.1 (October 2025) — Introduced citations/authors.master.yaml as the canonical author registry; added validation and split tooling.
	•	v1.2 (October 2025) — Adopted Bache Graph–formatted CSL-JSON citations with x-bache extension block, ensuring all entries are single-line, graph-ready, and fully normalized.

⸻

✅ The LSDMU Bibliography Registry now provides a complete, reproducible foundation for the Bache Graph — every citation, every author, every link.

⸻

🧭 Archival Status

This repository represents the final canonical release (v1.2)
of the LSD and the Mind of the Universe Bibliography Registry.
All data were validated and checksummed as of October 2025.
No further edits are planned; this registry is preserved for
scholarly and archival use under CC0 1.0.


---
All Wikidata QIDs and identifiers in this repository are maintained in the canonical registry:
[bache-archive-meta](https://github.com/bache-archive/bache-archive-meta)

