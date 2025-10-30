# Changelog — LSDMU Bibliography Registry

---

### v1.3 — October 30, 2025
- **Wikidata Enrichment**
  - Minted new QIDs:  
    N. Chwelos (Q136673052), Mark Bolstridge (Q136673055), Edith Fiore (Q136673082),  
    Joseph Havens (Q136673131), Bruce Leininger (Q136673138), Andrea Leininger (Q136673141),  
    Ken Gross (Q136673149), Winafred Blake Lucas (Q136673154), Morris Netherton (Q136673155),  
    James Oroc (Q136673158), Thomas Zinser (Q136673161), Duncan Blewett (Q136673193),  
    Hans Ten Dam (Q136673207).
  - Fixed mis-mapped QIDs:  
    Roger Walsh → Q3622980, Anne C. Klein → Q4768201, Paul Gilding → Q2754187,  
    S. L. Cranston → Q112421631, Walter Pahnke → Q7965779.
  - Added missing English labels (e.g. Dante Alighieri) and validated each entity’s `P31=Q5` (human).
  - Regenerated `citations/_manifests/enrichment_summary.csv` and verified all person QIDs (n = 109).

- **Repository Sync**
  - Regenerated split author YAMLs (`citations/authors/*.yaml`) to reflect new Wikidata enrichments.  
  - Cleaned tooling directory: added `orcid_audit.py`, `wikidata_audit.py`; removed backups and temporary scripts.  
  - Refreshed SHA256 manifests (`citations/_manifests/checksums.sha256`, `checksums/sha256sum_v1.2.txt`).  

---

### v1.2 — November 2025
- Rebuilt the full bibliography using the **LSDMU Bibliography Formatter** and **Author Formatter**.
- Published v1.2 release to GitHub, GitLab, Zenodo, and Internet Archive.  
- Implemented full CSL-JSON + `x-bache` structure for all entries.  
- Added complete provenance metadata (`entered_by`, `entered_at`, `notes`) across registry.  
- Integrated `validate_registry.py` and `normalize_csl.py` for schema-aware validation.  
- All entries revalidated under schema v1.2 and verified clean.

---

### v1.1 — October 2025
- Normalized 154 works (A–Z) from *LSD and the Mind of the Universe*.  
- Created 153 author YAML profiles.  
- Added Wikidata / ORCID / topical field enrichment.  
- Generated field changelog CSV.  
- Prepared schema & validation scaffolding.  
- Established directory and project documentation.

---

### v1.0 — September 2025
- Initial import and normalization of all bibliographic sources.  
- Defined baseline CSL-JSON structure and naming conventions.  
- Established canonical directory layout (`citations/`, `schema/`, `validation/`, `topics.yaml`).  
- Drafted project charter and README.
