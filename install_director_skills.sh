#!/bin/bash
# 破茧计划 — 编导Agent Skill包安装脚本
# 用法：bash install_director_skills.sh
# 安装后编导/管理员可在 WorkBuddy 中直接调用 director-core / admin / 各IP子包

set -e

SKILLS_DIR="$HOME/.workbuddy/skills"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)/packages"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ 找不到 packages 目录：$SOURCE_DIR"
    exit 1
fi

mkdir -p "$SKILLS_DIR"

# skill包列表
PACKAGES=(
    "director-core:编导母包"
    "admin:管理员包"
    "director-ip-biaoma_yeren:飙马野人IP子包"
    "director-ip-xinran_diary:心冉日记IP子包"
    "director-ip-xiee_dashubiao:邪恶大鼠标IP子包"
    "director-ip-fuxiaoxin:富小新IP子包"
    "director-ip-yeah:yeah IP子包"
    "director-ip-dongcai:董香菜IP子包"
)

TIMESTAMP=$(date +%s%N | cut -c1-16)

echo "📦 开始安装编导Agent Skill包..."
echo ""

installed=0
for entry in "${PACKAGES[@]}"; do
    pkg_name="${entry%%:*}"
    display_name="${entry##*:}"
    pkg_dir="$SOURCE_DIR/$pkg_name"
    skill_dir="$SKILLS_DIR/skill_${TIMESTAMP}_${pkg_name}"

    if [ ! -f "$pkg_dir/SKILL.md" ]; then
        echo "⚠️  跳过 $pkg_name（无SKILL.md）"
        continue
    fi

    # 创建skill目录
    mkdir -p "$skill_dir"
    cp "$pkg_dir/SKILL.md" "$skill_dir/"

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
    "installedAt": $TIMESTAMP,
    "source": "local_install",
    "version": "2.0.0",
    "skillId": "skill_${TIMESTAMP}_${pkg_name}",
    "examples_zh": [
        "加载$display_name",
        "用$pkg_name出稿",
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
