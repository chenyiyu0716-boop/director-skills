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

## 远程 Cowork：安装后告诉 Claude

把下面整段粘贴进对话（把 token 换成管理员私下下发的 secret）：

```text
API_BASE = https://goes-equation-william-chances.trycloudflare.com
我的 director token = <管理员私下下发的 secret>
我的 ip_id = ip_biaoma_yeren
请加载 director-core + director-ip-biaoma_yeren，按 Knowledge Proposal v2 流程工作。
```

换 IP 时只改 `ip_id` 与对应子包名（如 `director-ip-fuxiaoxin`）。

## 自检 Tunnel

```bash
curl -sS https://goes-equation-william-chances.trycloudflare.com/health
curl -sS -H "Authorization: Bearer <你的token>" \
  https://goes-equation-william-chances.trycloudflare.com/api/pipeline/me
```

期望：`health` 返回 `{"status":"ok"}`；`/me` 返回你的 role / ip_scope。

## 包内容

- `director-core` — 母技能（定稿 → Knowledge Proposal）
- `admin` — 管理员（知识提案中心审核）
- `director-ip-*` — 各 IP 子包（不含真实 token）
- `short-podcast-writer` — AI/工作/个体价值短播客选题、来源核验与 5 分钟初稿工作流
