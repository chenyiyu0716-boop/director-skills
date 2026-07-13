---
name: director-ip-yeah
description: "yeah IP 编导子包。当编导提到『yeah』『4岁国际生娃』『娃号 POV』或要为该抖音 IP 写商单/日常脚本、做选题对标复盘时使用。只声明 IP 身份与速查指针，真正的人设/风格/铁律由 director-core 母技能凭 ip_id 调 API 动态加载。需与 director-core 一起使用。"
---

# director-ip-yeah —— yeah 编导子包

## IP 身份
- `ip_id`: `ip_yeah`
- `ip_name`: yeah
- director token：由管理员私下下发（勿写入 skill / 文档 / 截图；会话内告知 Claude）

## 工作方式
1. 本子包只负责"我是 yeah"。加载后由 **director-core 母技能** 接管全部工作流。
2. 母技能凭本 `ip_id` + director token 调 API 动态加载六件套（含专属交付范式与大纲分段格式），不在此存人设正文，避免与库漂移。

## 本地速查（轻量）
- 平台：抖音；4 岁国际生娃 **孩子主视角（POV）** vlog，妈妈镜头外辅助。
- 账号冷启动中，定位/对标以 API 六件套为准（含 needs_review 标注）。
- 其余人设/铁律一律以 API 拉取为准。
