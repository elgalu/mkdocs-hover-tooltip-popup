#!/bin/bash
# Run pre-commit hooks via prek.
# In CI (CDP_BUILD_VERSION or CI set), runs only on changed files.
# Otherwise, runs on all files.
#
# Usage:
#   ./scripts/check.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
# shellcheck source=/dev/null
source .venv/bin/activate

# Lint only the files changed since a base ref when we can resolve a meaningful diff
# range, otherwise lint everything. The changed-files path needs: (1) a resolvable base
# ref, (2) shared history with HEAD (a merge-base), and (3) the base to differ from HEAD
# (else the diff is empty). GitHub Actions' default shallow checkout (fetch-depth: 1) and
# a push whose HEAD equals origin/main both fail those conditions, so CI falls back to
# --all-files — the repo is small and checking everything is fast and deterministic.
base_ref=""
for candidate in "${PREK_FROM_REF:-}" origin/HEAD origin/main origin/master; do
    [ -n "$candidate" ] || continue
    if git rev-parse --verify --quiet "$candidate" >/dev/null &&
        git merge-base "$candidate" HEAD >/dev/null 2>&1 &&
        [ "$(git rev-parse "$candidate")" != "$(git rev-parse HEAD)" ]; then
        base_ref="$candidate"
        break
    fi
done

if [ -n "$base_ref" ]; then
    uvx --from 'prek' prek run --show-diff-on-failure --from-ref "$base_ref" --to-ref HEAD
else
    uvx --from 'prek' prek run --all-files
fi
