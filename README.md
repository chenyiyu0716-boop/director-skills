# director-skills — 破茧计划编导 Agent Skill 包

Knowledge Proposal v2 版。Remote AI 回传只走 Knowledge Proposal，不直写知识库。

## 一键安装（WorkBuddy / 本机）

```bash
git clone https://github.com/chenyiyu0716-boop/director-skills.git
cd director-skills && bash install_director_skills.sh
```

已有旧目录时请先更新再安装：

```bash
cd director-skills && git pull && bash install_director_skills.sh
```

## 远程 Cowork：安装后配置运行环境

不要把 token 粘贴进模型对话。由管理员通过受控渠道下发，并在运行 Skill 的环境中配置：

```bash
export DIRECTOR_API_BASE="https://director.example.com"
export DIRECTOR_TOKEN="$(security find-generic-password -w -s director-agent -a "$USER")"
export DIRECTOR_IP_ID="ip_biaoma_yeren"
```

macOS 示例使用钥匙串；CI/服务器应使用各自的 secret manager。换 IP 时只改 `DIRECTOR_IP_ID` 与对应子包名（如 `director-ip-fuxiaoxin`）。

## 自检 Tunnel

```bash
curl -sS "$DIRECTOR_API_BASE/health"
curl -sS -H "Authorization: Bearer $DIRECTOR_TOKEN" \
  "$DIRECTOR_API_BASE/api/pipeline/me"
```

期望：`health` 返回 `{"status":"ok"}`；`/me` 返回你的 role / ip_scope。

## 包内容

- `director-core` — 母技能（定稿 → Knowledge Proposal）
- `admin` — 管理员（知识提案中心审核）
- `director-ip-*` — 各 IP 子包（不含真实 token）
- `short-podcast-writer` — AI/工作/个体价值短播客选题、来源核验与 5 分钟初稿工作流
