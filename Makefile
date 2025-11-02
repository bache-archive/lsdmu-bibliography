# Makefile — minimal, safe tabs, no heredocs
PY := python3
CIT_DIR := citations/registry
SCHEMA := schema/work.json
TOPICS := topics.yaml

.PHONY: format validate normalize check audit sample open-sample qid-sync qid-validate qid-all

format:
	@command -v jq >/dev/null 2>&1 || { echo "jq not found (optional). Skipping format."; exit 0; }
	@echo "Formatting JSON with jq (sorted keys)…"
	@find $(CIT_DIR) -type f -name '*.json' -exec sh -c 'f="$$1"; jq -S . "$$f" > "$$f.tmp" && mv "$$f.tmp" "$$f"' sh {} \;
	@echo "JSON formatted."

validate:
	@$(PY) validation/validate_registry.py
	@./scripts/validate_layout.sh

normalize:
	@$(PY) validation/normalize_csl.py

check: format normalize validate

audit:
	@$(PY) validation/audit_registry.py

sample:
	@$(PY) validation/make_sample.py

open-sample:
	@$(PY) validation/open_sample.py

# --- QID integration -------------------------------------------------------

qid-sync:
	@echo "🔄 Syncing Wikidata QIDs from bache-archive-meta…"
	@./scripts/qid_sync.py

qid-validate:
	@echo "✅ Validating QID alignment with bache-archive-meta…"
	@./scripts/qid_validate.py

qid-all: qid-sync qid-validate
	@echo "✔️  QID sync + validation complete."