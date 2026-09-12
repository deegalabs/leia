#!/usr/bin/env bash
# Creates an annotated tag for a hackathon delivery and appends a commit summary
# to the matching CHANGELOG.md section. Usage: scripts/tag-delivery.sh v0.2.0 "Entrega 2: V1 com testes internos"
set -euo pipefail
version="${1:?version, e.g. v0.2.0}"
message="${2:?message, e.g. 'Entrega 2: V1 com testes internos'}"
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [ -n "$(git status --porcelain)" ]; then
  echo "working tree not clean: commit first" >&2; exit 1
fi
if git rev-parse -q --verify "refs/tags/$version" >/dev/null; then
  echo "tag $version already exists" >&2; exit 1
fi

previous="$(git describe --tags --abbrev=0 2>/dev/null || true)"
range="${previous:+$previous..}HEAD"
summary="$(git log --no-merges --pretty='- %s' "$range")"
stamp="$(date '+%Y-%m-%d %H:%M')"

python3 - "$version" "$message" "$stamp" "$summary" <<'PY'
import re, sys
version, message, stamp, summary = sys.argv[1:5]
path = "CHANGELOG.md"
text = open(path, encoding="utf-8").read()
header = f"## {version}"
block = f"{header} · {stamp} · {message}\n{summary}\n"
pattern = re.compile(rf"^## {re.escape(version)}[^\n]*\n(?:_A preencher[^\n]*_\n)?", re.M)
if pattern.search(text):
    text = pattern.sub(block, text, count=1)
else:
    text = text.replace("\n## ", f"\n{block}\n## ", 1) if "\n## " in text else text + "\n" + block
open(path, "w", encoding="utf-8").write(text)
PY

git add CHANGELOG.md
git commit -q -m "chore(release): $version"
git tag -a "$version" -m "$message"
echo "tagged $version at $(git rev-parse --short HEAD)"
echo "next: fill evidence/<delivery>/MANIFEST.md and publish to the official folder"
