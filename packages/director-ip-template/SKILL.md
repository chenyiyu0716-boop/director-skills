---
name: director-ip-template
description: "【模板】某个具体 IP 的编导子包。新增 IP 时拷贝本目录、改名为 director-ip-<slug>，填好下方 ip_id 与触发关键词即可。它只声明 IP 身份与速查指针，真正的人设/风格/铁律由 director-core 母技能凭 ip_id 调 API 动态加载。需与 director-core 一起使用。"
---

# director-ip-template —— IP 编导子包（模板）

> 这是模板。新增 IP：复制本目录 → 改名 `director-ip-<slug>` → 改下面三处 → 完成。

## IP 身份（必填）
- `ip_id`: `ip_<slug>`            ← 改成真实 ip_id，如 ip_xinran_diary
- `ip_name`: 中文名               ← 如 心冉日记
- director token：由管理员私下下发（**勿**写入本文件）
- 触发关键词: 写进上方 frontmatter description（如"心冉""心冉日记""留学生脚本"）

## 工作方式
1. 本子包只负责"我是哪个 IP"。加载后，由 **director-core 母技能** 接管全部工作流。
2. 母技能凭本 `ip_id` + director token 调 API 动态加载该 IP 六件套，不在本子包里存人设正文（避免与库不一致）。

## 本地速查（可选，轻量）
仅放极少量高频速查（如该 IP 的输出文件命名习惯、特殊禁忌一两条）。**正文人设/风格/铁律一律放知识库、由 API 拉**，不要复制到这里，否则会与库漂移。

## 首批 5 个 IP 对应子包（task1/task3 落地）
- director-ip-biaoma_yeren（飙马野人）— 模板基准，资料最全
- director-ip-xiee_dashubiao（邪恶大鼠标）
- director-ip-fuxiaoxin（富小新）— 试用已开放（Excel/Street 脚本源，needs_review 段不编造）
- director-ip-yeah（yeah / 4岁国际生娃号）
- director-ip-xinran_diary（心冉日记）
