---
name: short-podcast-writer
description: "Create a repeatable short-podcast research and writing workflow for AI, work, and individual value. Use when the user asks for $short-podcast-writer, recent 7-day Douyin/interview source verification, topic selection, emotional resonance scoring, or a 5-minute marked short-podcast draft in a gentle early-Shuilian-like tone for 20-30 year-old small-town youth and white-collar listeners."
---

# Short Podcast Writer

Use this skill to turn recent AI/work/individual-value conversations into a verified short-podcast package: source table, 3 topic options, best-topic rationale, and a 5-minute draft with production marks.

## Core Position

Hold this editorial center:

- The audience is 20-30 year-old small-town youth and white-collar workers who feel career pressure, AI anxiety, and meaning fatigue.
- The tone is gentle, sensitive, clear, and inward-facing, inspired by the early "睡莲" feeling without copying wording.
- The core thesis is: individual spiritual abundance matters; feeling is the first antenna.
- Do not sell anxiety, success worship, or tool worship. AI is context, not the protagonist.

## Source Workflow

For each run, use a rolling 7-day window unless the user specifies otherwise.

1. Gather sources from Douyin videos, interview clips, livestream cuts, podcast clips, founder conversations, scholars, philosophers, AI practitioners, and adjacent media reports.
2. Prefer frontier conversations: Kimi/Moonshot-like founders, philosophy professors, reflective builders, ex-tech workers such as Guo Yu, and other people discussing work, freedom, value, and inner life.
3. Verify at minimum: source link, publish time, speaker/account, and concise original-speech summary.
4. Do not claim platform-wide hotness without platform-visible evidence. Say "可核验来源" or "近期传播素材" when ranking data is unavailable.
5. If using direct Douyin search, respect login/captcha/rate-limit stops. Do not bypass platform restrictions.

If local Douyin reference JSON already exists, it can be produced by `memory B`:

```bash
cd "memory B"
npm run reference:douyin -- --topic "AI 工作 个体价值" --keywords "Kimi创始人,北大哲学系教授,郭宇,AI时代工作" --lookback-days 7 --max-results 8
```

Then feed the JSON to the bundled report generator.

## Report Generator

Use `scripts/generate_report.py` when the user wants a reusable local workflow artifact or a consistent Markdown report from source data.

The script is **dual-mode**:

- **Generative (default when `LLM_API_KEY` is set)**: calls an LLM (packyapi Claude by default) to write the 3 topics and the 5-minute draft grounded in the actual verified sources, then renders the full report.
- **Template fallback (when no key / LLM call fails)**: reuses the original fixed scaffold so the script never hard-fails. The source table is always real; only the topics/draft fall back to templates.

### Source feed (pick one)

1. `--sources path/to/sources.json` — explicit JSON (list / `{sources:[...]}` / memory-B `{videos:[...]}`).
2. `--reference-dir <dir>` — read the newest `*douyin_reference.json` for the topic. **Defaults to the memory-B `logs/instant_reference` dir** (auto-detected; override with `--reference-dir` or env `MEMORY_B_REFERENCE_DIR` / `MEMORY_B_DIR`). This is the recommended feed for the 7-day Douyin workflow.
3. `--fetch-douyin` — live-run `npm run reference:douyin` from memory-B (needs a logged-in Douyin Playwright profile on the host). Extra flags: `--keywords`, `--max-results`, `--reference-lookback-days` (default 7), `--memory-b-dir`.
4. `--fetch-podcast` — live-run the **same** memory-B douyin search but **targeted at 抖音播客/音频** (podcast clips): it appends `播客`/`音频` to the keywords, lowers `--podcast-min-likes` (default 2000) and widens `--podcast-lookback-days` (default 30, since podcasts publish less often). Sources are tagged `platform=抖音播客` in the report. Same live-profile requirement as `--fetch-douyin`.

### Recommended run (7-day memory-B feed + generative)

```bash
export LLM_API_KEY="<packyapi key>"   # 不设置则自动回退模板
python3 director-skills/packages/short-podcast-writer/scripts/generate_report.py \
  --reference-dir "memory B/logs/instant_reference" \
  --topic "AI、工作与个体价值" \
  --keywords "Kimi创始人,北大哲学系教授,郭宇,AI时代工作" \
  --days 7 \
  --output outputs/short_podcast_report.md
```

Or trigger a fresh live pull instead of reading the latest file:

```bash
python3 director-skills/packages/short-podcast-writer/scripts/generate_report.py \
  --fetch-douyin --topic "AI、工作与个体价值" \
  --keywords "Kimi创始人,北大哲学系教授,郭宇" --reference-lookback-days 7 \
  --output outputs/short_podcast_report.md
```

Or pull real **podcast** clips (the full "抓播客" flow):

```bash
python3 director-skills/packages/short-podcast-writer/scripts/generate_report.py \
  --fetch-podcast --topic "AI、工作与个体价值" \
  --keywords "Kimi创始人,北大哲学系教授" \
  --output outputs/short_podcast_podcast.md
# window auto-defaults to 30 days; override with --days / --podcast-lookback-days.
```

> Live (`--fetch-douyin` / `--fetch-podcast`) needs a host Douyin Playwright profile clear of captcha/rate-limit. When the pull returns 0 (verification/rate-limit), the script warns and falls back to template — it never hard-fails.

### LLM configuration (env vars)

- `LLM_API_KEY` — required for generative mode (unset → template fallback).
- `LLM_BASE_URL` — default `https://www.packyapi.com/v1` (OpenAI-compatible).
- `LLM_MODEL` — default `claude-sonnet-5`.
- `LLM_FORMAT` — `openai_compatible` (default) or `anthropic` (native `/v1/messages`).

**How to set them:** the script auto-loads `<package>/.env` at startup (stdlib only, no deps), so you can persist the key there instead of exporting every time. Just fill in `LLM_API_KEY=` in `short-podcast-writer/.env`. `.env` is git-ignored — do not commit your key. You can also override any value via real environment variables.

The call uses only the Python standard library (no third-party deps). `references/voice-and-format.md` is auto-loaded into the LLM system prompt; read it before revising the style or templates.

### Output

A Markdown report with: source verification table, 3 topics (with scores + best-topic flag), best topic, 5-minute marked draft, title alternatives, release intro, comment prompt, and next-episode extensions. The report header records the active mode (`生成式（LLM）` or `模板回退`).

## Topic Selection

Return exactly 3 topics unless the user requests otherwise. Rank by:

- 50% propagation potential: title tension, shareability, zeitgeist relevance.
- 50% emotional resonance: whether it names the audience's real inner feeling without scolding them.

Each topic must include:

- Title
- One-line copy
- Sources
- Original-speech summary
- Emotional resonance point
- Propagation hook
- Recommendation score
- Whether it should become the 5-minute draft

## 5-Minute Draft

Write 900-1200 Chinese characters unless the user requests another length. Include production marks:

- `[开场]`
- `[来源引入]`
- `[情绪翻译]`
- `[观点展开]`
- `[生活落点]`
- `[结尾]`

Avoid commands like "你必须". Prefer "也许", "你可以先", "这件事值得被看见", and concrete inner-life observations.

## Delivery

Final delivery package:

1. Rolling-window source verification table
2. 3 topic options
3. Best-topic rationale
4. 5-minute marked draft
5. 3-5 title alternatives
6. Release intro
7. Comment prompt
8. Next-episode extension
