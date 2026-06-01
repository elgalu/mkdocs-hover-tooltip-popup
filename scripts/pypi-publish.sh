#!/bin/bash
# Publish the built distribution in dist/ to PyPI.
#
# Auth: set UV_PUBLISH_TOKEN to a PyPI API token (starts with "pypi-").
# Create one at https://pypi.org/manage/account/token/ (user: elgalu).
#
# Usage:
#   UV_PUBLISH_TOKEN=pypi-xxxx ./scripts/pypi-publish.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ -z "${UV_PUBLISH_TOKEN:-}" ]; then
    echo "Error: UV_PUBLISH_TOKEN is not set." >&2
    echo "  Create a token at https://pypi.org/manage/account/token/ and run:" >&2
    echo "    UV_PUBLISH_TOKEN=pypi-xxxx make pypi-publish" >&2
    exit 2
fi

if ! ls dist/*.whl >/dev/null 2>&1; then
    echo "Error: no artifacts in dist/. Run 'make pypi-build' first." >&2
    exit 2
fi

echo "Publishing dist/* to PyPI ..."
uv publish
echo "✓ Published to https://pypi.org/project/mkdocs-hover-tooltip-popup/"
