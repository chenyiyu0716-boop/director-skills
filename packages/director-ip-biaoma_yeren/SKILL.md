---
name: director-ip-biaoma_yeren
description: "飙马野人 IP 编导子包。当编导提到『飙马野人』『飙马』『野人』或要为该抖音 IP 写商单/日常脚本、做选题对标复盘时使用。只声明 IP 身份与速查指针，真正的人设/风格/铁律由 director-core 母技能凭 ip_id 调 API 动态加载。需与 director-core 一起使用。"
---

# director-ip-biaoma_yeren —— 飙马野人 编导子包

## IP 身份
- `ip_id`: `ip_biaoma_yeren`
- `ip_name`: 飙马野人
- director token：由管理员私下下发（勿写入 skill / 文档 / 截图；会话内告知 Claude）

## 工作方式
1. 本子包只负责"我是飙马野人"。加载后由 **director-core 母技能** 接管全部工作流。
2. 母技能凭本 `ip_id` + director token 调 API 动态加载六件套（含专属交付范式与大纲分段格式），不在此存人设正文，避免与库漂移。

## 本地速查（轻量）
- 平台：抖音；商单 vlog 为主。
- 大纲/脚本节奏走 generation-bundle 返回的飙马专属六段（1-10s / 10-20s / 20-35s / 35-55s / 55-75s / 75-90s），不要改成 0-10s/20-40s 等。
- 其余人设/铁律一律以 API 拉取为准。
