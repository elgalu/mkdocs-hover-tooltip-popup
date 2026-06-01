#!/bin/bash
# Publish the built distribution in dist/ to TestPyPI (a dry run before the real one).
#
# Auth: set UV_PUBLISH_TOKEN_TEST to a TestPyPI API token.
# Create one at https://test.pypi.org/manage/account/token/.
#
# Usage:
#   UV_PUBLISH_TOKEN_TEST=pypi-xxxx ./scripts/pypi-publish-test.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ -z "${UV_PUBLISH_TOKEN_TEST:-}" ]; then
    echo "Error: UV_PUBLISH_TOKEN_TEST is not set." >&2
    echo "  Create a token at https://test.pypi.org/manage/account/token/ and run:" >&2
    echo "    UV_PUBLISH_TOKEN_TEST=pypi-xxxx make pypi-publish-test" >&2
    exit 2
fi

if ! ls dist/*.whl >/dev/null 2>&1; then
    echo "Error: no artifacts in dist/. Run 'make pypi-build' first." >&2
    exit 2
fi

echo "Publishing dist/* to TestPyPI ..."
uv publish --publish-url https://test.pypi.org/legacy/ --token "$UV_PUBLISH_TOKEN_TEST"
echo "✓ Published to https://test.pypi.org/project/mkdocs-hover-tooltip-popup/"
