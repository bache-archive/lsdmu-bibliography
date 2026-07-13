#!/usr/bin/env bash
set -euo pipefail

OLD="Bache Archive Stewardship Team"
NEW="Bache Archive maintainer"

echo "🔍 Searching and replacing '${OLD}' → '${NEW}' ..."

# Only operate on text-based project files
FILES=$(git ls-files \
  | grep -E '\.(md|yaml|yml|json|txt)$' \
  | grep -v -E '(index\.faiss|\.zip|\.tgz|\.gz|\.pyc|\.png|\.jpg|\.jpeg|\.DS_Store)' || true)

for file in $FILES; do
  if grep -q "${OLD}" "$file"; then
    echo "📝 Updating: $file"
    # Use in-place substitution (compatible with macOS/BSD sed)
    sed -i '' "s/${OLD}/${NEW}/g" "$file"
  fi
done

echo "✅ Replacement complete."

# Optionally, show a quick diff summary
echo
echo "🔎 Modified files:"
git diff --name-only | sort

