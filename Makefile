# Makefile
PY := python3

CIT_DIR := citations/registry
SCHEMA := schema/work.json
TOPICS := topics.yaml

# Format all CSL-JSON files consistently with jq (if installed).
format:
	@command -v jq >/dev/null 2>&1 || { echo "jq not found (optional). Skipping format."; exit 0; }
	@find $(CIT_DIR) -type f -name '*.json' -print0 | xargs -0 -I {} sh -c 'jq -S . "{}" > "{}.tmp" && mv "{}.tmp" "{}"'
	@echo "JSON formatted."

# Validate against schema, filename<->id match, allowed topics, duplicate ids, author cross-refs
validate:
	@$(PY) validation/validate_registry.py

# Normalize minor field issues across all files (publisher-place spelling, language, topics, etc.)
normalize:
	@$(PY) validation/normalize_csl.py

# Run everything
check: format normalize validate
