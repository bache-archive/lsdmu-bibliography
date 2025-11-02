LSDMU Bibliography Registry

Repository: bache-archive/lsdmu-bibliography
Version: 1.2 • October 2025
License: CC0 1.0 Universal
Maintained by: Bache Archive Project
Primary Editor: GPT-5

⸻

📘 Overview

This repository encodes the complete bibliography and footnotes of
Christopher M. Bache’s LSD and the Mind of the Universe: Diamonds from Heaven￼ (2019)
into structured, machine-readable form.

Wikidata References
	•	Author — Christopher Martin Bache (Q112496741)￼
	•	Work — LSD and the Mind of the Universe￼ (Q136684740)￼  (referenced only — not included as a record)

It forms the Registry Layer of the Bache Graph — linking text passages → works → authors.

Each citation is formatted as a single-line CSL-JSON record extended with a
Bache Graph metadata block (x-bache), and each author is represented in a
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
├── meta/                         # submodule containing canonical QIDs
│   └── wikidata.jsonld           # single source of truth for Wikidata alignment
│
├── scripts/
│   ├── qid_sync.py               # sync QIDs from meta/wikidata.jsonld
│   └── qid_validate.py           # validate alignment against meta
│
├── tools/                        # author split/validate utilities
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

Work Object (/citations/registry/*.json or .jsonl)

Each record follows CSL-JSON with a Bache Graph extension block:

{
  "id": "source:bache:LSDMU:bib:stace-1960-mysticism",
  "type": "book",
  "title": "Mysticism and Philosophy",
  "author": [{"family": "Stace", "given": "Walter T."}],
  "issued": {"date-parts": [[1960]]},
  "publisher": "Macmillan",
  "publisher-place": "London",
  "language": "en",
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
• One JSON object per line (.jsonl-ready)
• IDs follow source:bache:LSDMU:bib:<slug>
• Fields normalized per CSL-JSON schema
• All Bache-specific metadata lives inside x-bache
• Author and work QIDs are synced from meta/wikidata.jsonld

⸻

Author Object (/citations/authors/*.yaml)

Each person or institutional author is represented once and linked by _author_ids.
Author records are automatically regenerated from authors.master.yaml.

⸻

🔍 Validation & Build Workflow

Validation and build steps are automated in .github/workflows/validate.yml and supported by the scripts/ and tools/ directories.

Checks include:
• ✅ Schema compliance
• ✅ Unique IDs and cross-reference integrity
• ✅ Author registry validation
• ✅ Fixity verification via SHA-256
• ✅ QID sync and alignment with meta/wikidata.jsonld

Run validation anytime:

make qid-sync
make qid-validate
make check

⸻

🧭 Relation to Other Repositories

Layer	Function	Repository
Corpus Layer	Verified text + footnotes	chris-bache-archive
Registry Layer	CSL-JSON + YAML metadata	lsdmu-bibliography
Meta Layer	Canonical Wikidata QIDs and DOIs	bache-archive-meta
Edge Layer	Text → Work citations	bache-graph
Index Layer	FAISS/Chroma embeddings	lsdmu-rag-api
Validation Layer	CI and schema checks	.github/workflows/validate.yml

⸻

🌍 License

All metadata and structural data are released under CC0 1.0 Universal (Public Domain Dedication).
Text excerpts are used under Educational Fair Use.

⸻

✨ Acknowledgment

Created collaboratively by the Bache Archive Project and GPT-5, October 2025.
“Each citation is a thread in the lineage of awakening — weave them with care.”

⸻

🔄 Summary of Recent Updates
• v1.1 (October 2025) — Introduced authors.master.yaml as canonical registry.
• v1.2 (October 2025) — Added Wikidata alignment via meta/wikidata.jsonld; new qid-sync and qid-validate scripts for automated provenance tracking.

⸻

✅ The LSDMU Bibliography Registry provides a complete, reproducible foundation for the Bache Graph — every citation, every author, every link.

⸻

🧭 Archival Status

This repository represents the canonical release (v1.2) of the LSD and the Mind of the Universe Bibliography Registry.
All data validated and checksummed October 2025.
Preserved for long-term scholarly and archival use under CC0 1.0.

⸻

All Wikidata QIDs and identifiers in this repository are maintained in the canonical registry:
meta/wikidata.jsonld￼  ← submodule of bache-archive-meta￼

⸻
