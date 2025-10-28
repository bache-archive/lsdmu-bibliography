```markdown
# Project Charter — LSDMU Bibliography Registry

**Version:** 1.1 **Date:** 2025-10-29  
**Parent Projects:** Chris Bache Archive → Bache Graph → Lumen Graph  
**Repository:** `bache-archive/lsdmu-bibliography`

---

## 1 · Purpose

To transform the complete footnote corpus of *LSD and the Mind of the Universe* (2019)  
into a machine-readable, citation-traceable registry of every work Christopher Bache referenced.

This serves as the **influence layer** of the Bache Graph  
and the prototype for the Lumen Graph citation ontology.

---

## 2 · Core Objectives

| Goal | Description | Deliverable |
|------|--------------|-------------|
| Normalize Bibliography | Convert every citation into CSL-JSON + canonical IDs | `/citations/registry/*.json` |
| Author Registry | Create YAML profiles (Wikidata, ORCID, fields) | `/citations/authors/*.yaml` |
| Citation Edges | Link each footnote to its segment ID | `/graph/edges/citations/*.yaml` |
| Index | Create vector embeddings for search | `/citations/index.faiss` |
| Validation | Automate schema and fixity checks | `.github/workflows/validate.yml` |

---

## 3 · Status — October 2025

✅ **Phase 1 Complete:**  
- 154 works normalized (A–Z)  
- 153 author YAML profiles created  
- Enrichment with Wikidata, ORCID, topical fields  
- Internal changelog and validation CSV  

🔜 **Next Phases:**  
- Build citation edges (`bache-graph/`)  
- Generate FAISS embeddings  
- Publish v1.0 Zenodo DOI snapshot  

---

## 4 · Integration

| Layer | Function | Repository |
|--------|-----------|------------|
| Corpus | Extracted text & footnotes | `chris-bache-archive` |
| Registry | Bibliography & authors | `lsdmu-bibliography` |
| Edges | Passage → Work relations | `bache-graph` |
| Index | Semantic search store | `lsdmu-rag-api` |

---

## 5 · License & Ethics

- Metadata: CC0 1.0 Universal  
- Text excerpts: Educational Fair Use  
- Each edge includes curator & confidence  
- Every release includes checksum & validation report  

---

## 6 · Guiding Principle

> **Represent, don’t reinterpret.**  
> Our work is to preserve relational truth faithfully and reverently.
