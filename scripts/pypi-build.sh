#!/bin/bash
# Build the PyPI distribution (sdist + wheel) into dist/ and validate it.
#
# Usage:
#   ./scripts/pypi-build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "Cleaning old dist/ ..."
rm -rf dist

echo "Building sdist + wheel with uv ..."
uv build

echo "Validating artifacts with twine check ..."
uvx twine check dist/*

echo "✓ Built and validated:"
ls -1 dist/
