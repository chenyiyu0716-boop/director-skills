#!/bin/bash
# 破茧计划 — 编导Agent Skill包安装脚本
# 用法：bash install_director_skills.sh
# 安装后编导/管理员可在 WorkBuddy 中直接调用 director-core / admin / 各IP子包

set -euo pipefail

SKILLS_DIR="${WORKBUDDY_SKILLS_DIR:-$HOME/.workbuddy/skills}"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)/packages"
PACKAGE_VERSION="${DIRECTOR_SKILLS_VERSION:-2.0.0}"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ 找不到 packages 目录：$SOURCE_DIR"
    exit 1
fi

mkdir -p "$SKILLS_DIR"

PACKAGES=()
while IFS= read -r pkg_dir; do
    PACKAGES+=("$pkg_dir")
done < <(find "$SOURCE_DIR" -mindepth 2 -maxdepth 2 -name SKILL.md -print \
    | sed 's#/SKILL.md$##' | sort)

echo "📦 开始安装编导Agent Skill包..."
echo ""

installed=0
for pkg_dir in "${PACKAGES[@]}"; do
    pkg_name="$(basename "$pkg_dir")"
    display_name="$pkg_name"
    skill_dir="$SKILLS_DIR/skill_${pkg_name}"

    if [ ! -f "$pkg_dir/SKILL.md" ]; then
        echo "⚠️  跳过 $pkg_name（无SKILL.md）"
        continue
    fi

    # 使用稳定目录名做幂等升级，并复制完整包资源。
    rm -rf "$skill_dir"
    mkdir -p "$skill_dir"
    cp -R "$pkg_dir"/. "$skill_dir"/

    # 生成 workbuddy.json
    cat > "$skill_dir/workbuddy.json" << EOF
{
    "display_name": "$display_name",
    "display_name_en": "$pkg_name",
    "description_zh": "破茧计划编导Agent — $display_name",
    "description_en": "Director Agent — $display_name"
}
EOF

    # 生成 _skillhub_meta.json
    cat > "$skill_dir/_skillhub_meta.json" << EOF
{
    "name": "$pkg_name",
    "installedAt": $(date +%s),
    "source": "local_install",
    "version": "$PACKAGE_VERSION",
    "skillId": "skill_${pkg_name}",
    "examples_zh": [
        "加载$display_name",
        "用${pkg_name}出稿",
        "$display_name 帮我写脚本"
    ],
    "examples_en": [
        "Load $pkg_name"
    ]
}
EOF

    echo "✅ $display_name ($pkg_name) → $skill_dir"
    installed=$((installed + 1))
done

echo ""
echo "🎉 安装完成！共安装 $installed 个Skill包"
echo ""
echo "📋 使用方法："
echo "   1. 重启 WorkBuddy（或新开对话窗口）"
echo "   2. 在对话中输入：加载 director-core"
echo "   3. 或直接说：用飙马野人出稿"
echo ""
echo "⚠️  注意：编导需先加载 director-core 母包，再加载对应IP子包"
echo "📌 本包为 Knowledge Proposal v2：定稿回传 → POST /api/knowledge-proposals（或 trial-feedback Adapter）"
echo "   AI 不直写知识库，不调用 skill_iteration"
echo "   管理员加载 admin 包即可"
