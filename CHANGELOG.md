---
# Changelog — LSDMU Bibliography Registry

### v1.3 — November 2025
- Implemented structural and validation upgrades following the v1.2 release  
- Updated **manifests** across the registry to align with the new `x-bache` schema requirements  
- Refined **validation scripts** (`validate_registry.py`, `normalize_csl.py`)  
  - Enforce strict `id` pattern: `source:bache:LSDMU:bib:<slug>`  
  - Validate `x-bache` namespace, review_state, and citation_shorthand  
  - Add optional warnings for page formatting, missing language, and author/editor presence  
- Replaced and upgraded:
  - **`schema/work.json`** — now includes explicit `x-bache` definition, `review_state` enum, `original-date`, and strict provenance fields  
  - **`topics.yaml`** — alphabetized, expanded vocabulary (adds *participatory-spirituality*, *perinatal*, *species-evolution*, *consciousness-studies*), and includes `$schema` header  
- Verified all bibliography entries and author manifests against the new schema; zero errors after normalization  
- Maintained backward compatibility for archival versions on GitHub, Zenodo, GitLab, and Internet Archive

### v1.2 — November 2025
- Rebuilt the full bibliography using the **LSDMU Bibliography Formatter** and dedicated **Author Formatter**
- Published v1.2 release to **GitHub**, **GitLab**, **Zenodo**, and the **Internet Archive**
- Implemented full CSL-JSON + `x-bache` structure for all entries
- Added complete provenance metadata (`entered_by`, `entered_at`, `notes`) across registry
- Integrated `validate_registry.py` and `normalize_csl.py` scripts for schema-aware validation and normalization
- All entries revalidated under schema v1.2 and verified clean

### v1.1 — October 2025
- Normalized 154 works (A–Z) from *LSD and the Mind of the Universe*
- Created 153 author YAML profiles
- Added Wikidata / ORCID / topical field enrichment
- Generated field changelog CSV
- Prepared schema & validation scaffolding
- Established directory and project documentation

### v1.0 — September 2025
- Initial import and manual normalization of all bibliographic sources
- Defined baseline CSL-JSON structure and naming conventions
- Established canonical directory layout (`citations/registry/`, `schema/`, `validation/`, `topics.yaml`)
- Drafted project charter and README
## 2025-10-30

### Wikidata Enrichment
- Minted new QIDs: N. Chwelos (Q136673052), Mark Bolstridge (Q136673055), Edith Fiore (Q136673082),
  Joseph Havens (Q136673131), Bruce Leininger (Q136673138), Andrea Leininger (Q136673141),
  Ken Gross (Q136673149), Winafred Blake Lucas (Q136673154), Morris Netherton (Q136673155),
  James Oroc (Q136673158), Thomas Zinser (Q136673161), Duncan Blewett (Q136673193),
  Hans Ten Dam (Q136673207).
- Fixed mis-mapped QIDs: Roger Walsh → Q3622980, Anne C. Klein → Q4768201,
  Paul Gilding → Q2754187, S. L. Cranston → Q112421631, Walter Pahnke → Q7965779.
- Added missing en labels where needed (e.g., Dante Alighieri).

### Audits
- Ran human check (P31=Q5) across all person QIDs; resolved non-human outliers.
- Regenerated enrichment summary.

