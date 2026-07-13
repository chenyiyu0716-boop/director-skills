# packages/ —— 编导包 与 管理员包

两类"包"= Claude Skill（指令/工作流层）。agent 读完包后，带 token 调本机 LAN API / HTTPS 隧道操作知识库。
权限不在包里强制，而在 API 服务端按 token 的 `{role, ip_scope}` 强制；包负责"怎么做"，API 负责"能做什么"。

```
packages/
├── director-core/          母 skill：通用编导工作流（所有 IP 共用，与 IP 无关）
├── director-ip-<slug>/     每 IP 一个轻量子包（只装人设指针，运行时凭 ip_id 拉上下文）
│   └── director-ip-template/   ← 子包模板，新增 IP 拷贝改名即可
└── admin/                  管理员 skill：审批 / 动态库读写 / 治理
```

## 分发说明（Knowledge Proposal v2）

`director-core` / `admin` 已升级为 **Knowledge Proposal v2** 回传流程。试用编导若仍加载旧包，会按旧 pipeline proposal 话术行事。

**需要重新发 skill 包**（至少 `director-core`；IP 子包若含硬编码 token 也请换成新版）：

1. 把更新后的 `packages/director-core` + 对应 `director-ip-<slug>` 交给编导重新加载。
2. 对话里只告知：`API_BASE`（隧道 https）+ 私下下发的 director token + `ip_id`。
3. **不要**把真实 token 写进 skill 文件、飞书群公告或截图。

隧道 URL：若 tunnel 未重启且仍可用，可继续用旧 `API_BASE`；重启 quick tunnel 后 URL 会变，需同步更新。

## 两类包的核心区分

| 维度 | 编导包（director-core + IP 子包） | 管理员包（admin） |
|---|---|---|
| 用谁 | 各 IP 编导，每人 1 个 director token（绑定单一 ip_id） | 管理员，admin token（ip_scope=`*`） |
| 读 | 本 IP 静态库 + 共享热点 + 本 IP 白名单 | 全部静态/动态库 |
| 写静态库 | ❌ 不能直接写；提交 Knowledge Proposal | ✅ 知识提案中心 Approve → Admin submit → Relay |
| 写动态库 | ❌ | ✅ 读写、纠错、下线 |
| 生成脚本 | ✅ 商单线 + 日常线 + 打分门 | （一般不生成，可代跑） |
| 治理 | ❌ | ✅ IP 新增/下线、token 签发吊销、人设生成、打分校准、索引重建 |

详见 docs/17（总方案）、docs/31（上手）、docs/32（隧道）。
