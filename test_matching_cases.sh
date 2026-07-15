#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEXT_FILE="$ROOT_DIR/inputs/text.txt"
TMP_DIR="${TMPDIR:-/tmp}/pattern_matching_cases"

mkdir -p "$TMP_DIR"

cat > "$TMP_DIR/exact_patterns.txt" <<'PATTERNS'
vivamus.
PATTERNS

cat > "$TMP_DIR/wildcard_patterns.txt" <<'PATTERNS'
vi*amus.
PATTERNS

cat > "$TMP_DIR/approx_patterns.txt" <<'PATTERNS'
vivaaus.
PATTERNS

cmake --build "$ROOT_DIR/build"

echo
echo "================ Exact matching ================"
"$ROOT_DIR/build/pattern_matching" --text "$TEXT_FILE" --pattern "$TMP_DIR/exact_patterns.txt"

echo
echo "=============== Wildcard matching =============="
"$ROOT_DIR/build/pattern_matching" --text "$TEXT_FILE" --pattern "$TMP_DIR/wildcard_patterns.txt"

echo
echo "============= Approximate matching ============="
"$ROOT_DIR/build/pattern_matching" --text "$TEXT_FILE" --pattern "$TMP_DIR/approx_patterns.txt" --threshold 7
