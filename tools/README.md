# 📚 Author Enrichment Tools — ORCID + Wikidata Pipelines

This folder contains all the helper scripts used to enrich, verify, and apply **ORCID** and **Wikidata** identifiers to the author records in the LSDMU Bibliography Registry.

---

## 🌐 Purpose

The goal of these pipelines is to connect every author in  
`citations/authors.master.yaml` with verified global identifiers:
- **ORCID** → persistent researcher IDs for modern academics.
- **Wikidata QIDs** → canonical entities for both historical and living figures.

These enrichments anchor the Bache Graph’s author layer in stable, cross-dataset provenance.

---

## 🧩 Overview of the Process

Each enrichment (ORCID / Wikidata) follows the same general pattern:

| Step | Script | Description | Output |
|------|---------|-------------|---------|
| 1️⃣ | `orcid_candidates.py` / `wikidata_candidates.py` | Query external APIs (OpenAlex, ORCID, Crossref, Wikidata) for likely matches. | `citations/_manifests/orcid_candidates.csv`<br>`citations/_manifests/wikidata_candidates.csv` |
| 2️⃣ | `orcid_rank.py` / `wikidata_rank.py` | Assign heuristic scores to candidates (string match, initials, etc.). | `citations/_manifests/orcid_review.csv`<br>`citations/_manifests/wikidata_review.csv` |
| 3️⃣ | `orcid_seed_strict.py` / `wikidata_seed_strict.py` | Autoselect obvious, high-confidence matches for batch approval. | `citations/_manifests/orcid_approved.csv`<br>`citations/_manifests/wikidata_approved.csv` |
| 4️⃣ | (optional) manual review | Manually inspect or edit the `*_approved.csv` files to remove or correct edge cases. | same `*_approved.csv` |
| 5️⃣ | `orcid_apply.py` / `wikidata_apply.py` | Merge approved identifiers into `citations/authors.master.yaml`. | updates in-place |
| 6️⃣ | `authors_split.py` | Re-emit one YAML file per author from the updated master. | `citations/authors/*.yaml` |

---

## 🧠 How It Works

Each `*_apply.py` script:
1. Reads the approved manifest CSV.
2. Loads `citations/authors.master.yaml`.
3. Updates the matching author entries (`id` field) with:
   - `orcid: XXXX-XXXX-XXXX-XXXX`
   - `wikidata: QXXXXX`
4. Writes the YAML back out.
5. You then re-split into individual author files.

The `*_seed_strict.py` scripts use fuzzy matching (via **rapidfuzz**) to pre-approve only high-certainty hits, while leaving ambiguous ones for human review.

---

## 📁 Key Output Locations

| Path | Description |
|------|--------------|
| `citations/_manifests/` | All intermediate CSV manifests (candidates, review, approved). |
| `citations/_cache/` | HTTP cache for API queries to avoid rate limits. |
| `citations/authors.master.yaml` | Canonical full author registry (the source of truth). |
| `citations/authors/*.yaml` | Individual author files generated from the master. |

---

## 🔄 Typical Run Order

```bash
# ORCID Enrichment
python3 tools/orcid_candidates.py
python3 tools/orcid_rank.py
python3 tools/orcid_seed_strict.py
# (optional manual review)
python3 tools/orcid_apply.py citations/_manifests/orcid_approved.csv
python3 tools/authors_split.py

# Wikidata Enrichment
python3 tools/wikidata_candidates.py
python3 tools/wikidata_seed_strict.py
# (optional manual review)
python3 tools/wikidata_apply.py citations/_manifests/wikidata_approved.csv
python3 tools/authors_split.py


⸻

🧭 Version Control Tips
	•	Always commit and tag after each enrichment phase:
	•	vYYYY.MM.DD-orcid-seeding
	•	vYYYY.MM.DD-wikidata-pass
	•	Avoid running the apply steps without staging/committing your previous master file.
	•	The _cache directory should be git-ignored (already handled).

⸻

🧾 Provenance Philosophy

Each added identifier acts as a semantic anchor for the Bache Graph:
	•	ORCID ensures modern academic provenance and cross-database merge safety.
	•	Wikidata bridges historical, spiritual, and philosophical figures to broader knowledge networks.
	•	The process maintains full reproducibility via plain CSV manifests and YAML deltas.

⸻

🧰 Dependencies

pip install requests pyyaml rapidfuzz jq


⸻

✳️ Maintainer Notes
	•	The process is idempotent — re-running with the same approved CSVs will not duplicate data.
	•	If a new author is added to the master file, simply re-run the relevant candidate and seed scripts.
	•	For future improvements: integrate wikibase-api and orcid-public for richer metadata fetches.

⸻

Authored 2025-10-29 by the Bache Archive Stewardship Team
