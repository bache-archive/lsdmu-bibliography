# Architecture — LSDMU Bibliography Registry

**Repository:** bache-archive/lsdmu-bibliography  
**Version:** 1.0  
**Maintained by:** Bache Archive Stewardship Team

---

## System Overview

The LSDMU Bibliography Registry is one of five coordinated layers in the Bache Archive ecosystem:

| Layer | Function | Repository |
|--------|-----------|------------|
| Corpus | Verified source text + footnotes | `chris-bache-archive/` |
| Registry | CSL-JSON + YAML metadata for cited works | `lsdmu-bibliography/` |
| Edge | Citation relations (Text → Work) | `bache-graph/` |
| Index | Embedding + semantic retrieval | `lsdmu-rag-api/` |
| Validation | Schema + provenance testing | `.github/workflows/validate.yml` |

---

## Data Flow

1. **Input:** Footnote extraction from LSDMU text corpus  
2. **Normalization:** CSL-JSON + canonical IDs  
3. **Author Mapping:** YAML profiles with Wikidata/ORCID  
4. **Edge Creation:** Link text segments → Work IDs  
5. **Embedding:** Generate vector representations  
6. **Validation:** JSON Schema + SHACL integrity checks  
7. **Publication:** Commit + tag + Zenodo archive

---

## Integration Targets

- **Bache Graph:** Adds `cites` edges for every LSDMU passage  
- **Lumen Graph:** Integrates ontology nodes for `Work`, `Author`, `Topic`, `Relation`
