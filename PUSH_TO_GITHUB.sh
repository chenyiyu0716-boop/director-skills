#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
rm -rf .git
git init -b main
git remote add origin https://github.com/chenyiyu0716-boop/director-skills.git
git add -A
git commit -m "Release Knowledge Proposal v2 skill packs"
git push -u origin HEAD:main --force
echo "✅ 已推送到 https://github.com/chenyiyu0716-boop/director-skills"
