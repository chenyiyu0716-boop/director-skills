---
name: director-ip-fuxiaoxin
description: "富小新 IP 编导子包。当编导提到『富小新』『fuxiaoxin』时使用本子包声明身份；人设/风格/铁律由 director-core 凭 ip_id 调 API 加载（含 Street/Excel 过往脚本摘要）。需与 director-core 一起使用。"
---

# director-ip-fuxiaoxin —— 富小新 编导子包

## IP 身份
- `ip_id`: `ip_fuxiaoxin`
- `ip_name`: 富小新
- director token：由管理员通过受控密钥渠道下发；运行时从 `DIRECTOR_TOKEN` 环境变量或密钥存储读取，勿写入 skill、文档、聊天记录或截图

## 工作方式
1. 本子包只负责"我是富小新"。加载后由 **director-core 母技能** 接管全部工作流。
2. 母技能凭本 `ip_id` + director token 调 API 动态加载六件套与 generation-bundle；动态上下文见 `/pipeline/context/{ip_id}`（memory-A / memory-B / Street）。

## 本地速查（轻量）
- 过往脚本来自 Street/Excel 入库；六件套未齐处标 needs_review，不编造。
- 其余人设/铁律一律以 API 拉取为准。
