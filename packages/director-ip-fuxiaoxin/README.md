# director-ip-fuxiaoxin —— 富小新

- 知识库：六件套部分为 needs_review；过往脚本来源 **Street / Excel** 入库摘要。
- **试用已开放**：`GET /api/pipeline/static/generation-bundle/ip_fuxiaoxin` 正常返回 bundle；配合 memory-A / memory-B / Street 动态上下文出稿。
- director token：由管理员通过受控密钥渠道下发。运行时从 `DIRECTOR_TOKEN` 环境变量或密钥存储读取，禁止写入仓库、Skill、聊天记录或截图。

子包 SKILL.md 仅声明 `ip_id` / token / 触发词；人设铁律不复制于此，一律由 API 拉取。
