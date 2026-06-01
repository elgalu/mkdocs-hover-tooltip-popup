#!/bin/bash
# Bump the project version in pyproject.toml.
#
# Usage:
#   ./scripts/version-bump.sh [patch|minor|major]   (default: patch)
#
# Prints "old -> new" and leaves the change unstaged for review. Does NOT commit
# or tag (keep that an explicit, separate step).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PART="${1:-patch}"
case "$PART" in
    patch | minor | major) ;;
    *)
        echo "Error: bump part must be one of: patch, minor, major (got '$PART')" >&2
        exit 2
        ;;
esac

# Compute old/new from pyproject's [project] version using tomllib (stdlib 3.11+),
# falling back to a regex for older interpreters.
read -r OLD NEW < <(python3 - "$PART" <<'PY'
import re
import sys

part = sys.argv[1]
text = open("pyproject.toml", encoding="utf-8").read()

m = re.search(r'(?m)^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', text)
if not m:
    sys.exit("Could not find a semantic version in pyproject.toml")

major, minor, patch = (int(g) for g in m.groups())
old = f"{major}.{minor}.{patch}"
if part == "major":
    major, minor, patch = major + 1, 0, 0
elif part == "minor":
    minor, patch = minor + 1, 0
else:
    patch += 1
print(old, f"{major}.{minor}.{patch}")
PY
)

# Replace only the [project] version line (anchored), not arbitrary other matches.
python3 - "$OLD" "$NEW" <<'PY'
import re
import sys

old, new = sys.argv[1], sys.argv[2]
path = "pyproject.toml"
text = open(path, encoding="utf-8").read()
updated, n = re.subn(
    r'(?m)^(version\s*=\s*")' + re.escape(old) + r'(")',
    r"\g<1>" + new + r"\g<2>",
    text,
    count=1,
)
if n != 1:
    sys.exit(f"Expected to replace exactly one version line, replaced {n}")
open(path, "w", encoding="utf-8").write(updated)
PY

# Keep the lockfile's own project entry in sync (its version mirrors pyproject).
if command -v uv >/dev/null 2>&1; then
    uv lock --quiet >/dev/null 2>&1 || true
fi

echo "Version bumped ($PART): $OLD -> $NEW"
echo "Review the change, then commit/tag it before publishing."
