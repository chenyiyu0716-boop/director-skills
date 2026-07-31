#!/usr/bin/env python3
"""Generate a short-podcast research package from verified source JSON.

Two modes:
  - Generative (default when LLM_API_KEY is set): the script calls an LLM
    (packyapi Claude by default) to write the 3 topics and the 5-minute draft
    grounded in the actual verified sources.
  - Template fallback (when no key / LLM call fails): the original hardcoded
    scaffold is used so the script never hard-fails.

Source feed:
  - --sources <json>        : explicit source JSON (list / {sources:[...]} / memory-B {videos:[...]})
  - --reference-dir <dir>   : read the newest *douyin_reference.json (default: memory-B logs dir)
  - --fetch-douyin          : live-run `npm run reference:douyin` from memory-B (video search)
  - --fetch-podcast         : live-run memory-B douyin search targeted at 抖音播客/音频 podcast clips

No third-party dependencies: uses only the Python standard library (urllib,
subprocess, glob, ...).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_TOPIC = "AI、工作与个体价值"

# memory-B auto-detect candidates. Environment variables take precedence;
# remaining fallbacks are user-home or repository-relative, never machine-specific.
_MEMORY_B_REFERENCE_CANDIDATES = [
    value
    for value in (
        os.environ.get("MEMORY_B_REFERENCE_DIR"),
        str(Path.home() / "repos" / "memory-b" / "logs" / "instant_reference"),
        str(Path(__file__).resolve().parents[4] / "memory-b" / "logs" / "instant_reference"),
    )
    if value
]
_MEMORY_B_ROOT_CANDIDATES = [
    value
    for value in (
        os.environ.get("MEMORY_B_ROOT"),
        str(Path.home() / "repos" / "memory-b"),
        str(Path(__file__).resolve().parents[4] / "memory-b"),
    )
    if value
]


# ---------------------------------------------------------------------------
# Minimal .env loader (no third-party deps). Loads <package>/.env if present so
# the user can persist LLM_API_KEY etc. without exporting in every shell.
# ---------------------------------------------------------------------------
def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        with env_path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


_load_dotenv()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class Source:
    title: str
    speaker: str
    platform: str
    url: str
    published_at: str
    published_date: date | None
    quote_summary: str
    relevance: str
    raw_time: str
    likes: int | None
    verification_status: str


@dataclass
class TopicOption:
    title: str
    copy: str
    emotional_point: str
    hook: str
    score: int
    source_indexes: list[int]


# Default template copy (used only in fallback mode).
DEFAULT_RELEASE_INTRO = (
    "这期想聊的不是AI会不会替代我们，而是当世界越来越崇拜效率时，"
    "我们还能不能把自己的感受当成第一份真实资料。"
)
DEFAULT_COMMENT_PROMPT = "最近一次让你觉得“我好像不该忽略这个感受”的瞬间是什么？"
DEFAULT_NEXT_EPISODE = [
    "把自己当AI原生公司之前，如何先照顾好自己这个人。",
    "AI时代的文科能力：表达、感受、判断为什么重新变贵。",
    "当工作越来越像系统，人如何保留一小块不被优化的生活。",
]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a verified short-podcast topic package and 5-minute draft "
        "(generative via LLM when LLM_API_KEY is set, template fallback otherwise)."
    )
    parser.add_argument("--sources", help="Explicit source JSON file (list / {sources:[...]} / memory-B {videos:[...]}).")
    parser.add_argument("--reference-dir", help="Dir of memory-B douyin_reference JSON files; reads newest matching topic.")
    parser.add_argument("--fetch-douyin", action="store_true", help="Live-run memory-B `npm run reference:douyin` (video search).")
    parser.add_argument("--fetch-podcast", action="store_true", help="Live-run memory-B douyin search targeted at 抖音播客/音频 (podcast clips).")
    parser.add_argument("--memory-b-dir", help="memory-B project root (for --fetch-douyin / --fetch-podcast).")
    parser.add_argument("--keywords", default="", help="Comma-separated extra keywords for --fetch-douyin / --fetch-podcast.")
    parser.add_argument("--max-results", type=int, default=5, help="Max items to fetch.")
    parser.add_argument("--max-scrolls", type=int, default=2, help="Max search-result scrolls per keyword (keeps live fetch within timeout on software-rendered Chrome).")
    parser.add_argument("--reference-lookback-days", type=int, default=7, help="Lookback window for --fetch-douyin.")
    parser.add_argument("--podcast-lookback-days", type=int, default=30, help="Lookback window for --fetch-podcast (podcasts publish less often).")
    parser.add_argument("--podcast-min-likes", type=int, default=2000, help="Min likes for --fetch-podcast (lower than the video default).")
    parser.add_argument("--output", required=True, help="Markdown output path.")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="Research theme.")
    parser.add_argument("--days", type=int, default=None, help="Rolling source window (default 7; 30 when --fetch-podcast).")
    parser.add_argument(
        "--as-of",
        default=date.today().isoformat(),
        help="Report date, YYYY-MM-DD. Defaults to today.",
    )
    args = parser.parse_args()
    if args.days is None:
        args.days = 30 if args.fetch_podcast else 7
    return args


def main() -> None:
    args = parse_args()
    as_of = parse_as_of(args.as_of)
    raw = resolve_sources(args)
    sources = normalize_sources(raw, as_of)
    window_start = as_of - timedelta(days=args.days - 1)
    in_window = filter_sources(sources, window_start, as_of)
    active = in_window or sources

    llm_payload = None
    if has_llm_key():
        voice_text = read_voice_guide()
        llm_payload = generate_payload(args.topic, args.days, active, voice_text)
        if llm_payload is None:
            print("[warn] LLM 生成失败或返回无效结构，回退到模板。", file=sys.stderr)
    else:
        print("[info] 未检测到 LLM_API_KEY，使用模板回退（结构与来源核验真实，选题/稿件为固定模板）。", file=sys.stderr)

    report = render_report(
        topic=args.topic,
        days=args.days,
        as_of=as_of,
        window_start=window_start,
        sources=in_window,
        all_sources=sources,
        llm_payload=llm_payload,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(str(output))


# ---------------------------------------------------------------------------
# Source resolution (--sources / --reference-dir / --fetch-douyin)
# ---------------------------------------------------------------------------
def resolve_sources(args: argparse.Namespace) -> Any:
    if args.sources:
        return read_json(Path(args.sources))
    if args.fetch_podcast:
        return fetch_podcast(args)
    if args.fetch_douyin:
        return fetch_douyin(args)
    ref_dir = resolve_reference_dir(args.reference_dir)
    if ref_dir:
        path = load_reference_file(ref_dir, args.topic)
        if path:
            print(f"[info] 读取 memory-B 即时参考：{path}", file=sys.stderr)
            return read_json(Path(path))
        print(f"[warn] 在 {ref_dir} 未找到即时参考文件，且无 --sources。", file=sys.stderr)
    raise SystemExit("未提供来源：请传 --sources、--reference-dir（自动读最新文件）或 --fetch-douyin。")


def resolve_reference_dir(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env = os.environ.get("MEMORY_B_REFERENCE_DIR")
    if env and os.path.isdir(env):
        return env
    env2 = os.environ.get("MEMORY_B_DIR")
    if env2 and os.path.isdir(os.path.join(env2, "logs", "instant_reference")):
        return os.path.join(env2, "logs", "instant_reference")
    for candidate in _MEMORY_B_REFERENCE_CANDIDATES:
        if os.path.isdir(candidate):
            return candidate
    return None


def resolve_memory_b_dir(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env = os.environ.get("MEMORY_B_DIR")
    if env and os.path.isdir(env):
        return env
    for candidate in _MEMORY_B_ROOT_CANDIDATES:
        if os.path.isdir(candidate):
            return candidate
    return None


def load_reference_file(ref_dir: str, topic: str) -> str | None:
    safe = re.sub(r"[^\w-]+", "_", topic)[:36]
    files = glob.glob(os.path.join(ref_dir, "*douyin_reference.json"))
    if not files:
        return None
    matched = [f for f in files if safe in os.path.basename(f)]
    pool = matched or files
    return max(pool, key=lambda f: os.path.getmtime(f))


def _cdb_env() -> None:
    """Inject DOUYIN_CDP_URL + HEADLESS into the current process env so the
    memory-B `reference:douyin` subprocess (which we let inherit the full env)
    routes through CDP to a running real Chrome (default http://127.0.0.1:9223).
    With memory-B's preferPersistent=false, DOUYIN_CDP_URL makes it reuse the
    trusted real-Chrome session instead of Playwright's bundled Chromium."""
    os.environ["DOUYIN_CDP_URL"] = os.environ.get("DOUYIN_CDP_URL", "http://127.0.0.1:9223")
    os.environ["HEADLESS"] = "false"


def _check_cdp() -> bool:
    """Warn (non-fatal) if the real-Chrome CDP endpoint is not reachable."""
    import urllib.request

    cdp = os.environ.get("DOUYIN_CDP_URL", "http://127.0.0.1:9223")
    try:
        with urllib.request.urlopen(cdp.rstrip("/") + "/json/version", timeout=4) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        print(
            "[warn] 未检测到真实 Chrome 的 CDP 端点（%s）。\n"
            "       请先启动真实 Chrome 并在其中登录/通过抖音验证：\n"
            '         "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\\n'
            "           --no-sandbox --disable-gpu --remote-debugging-port=9223 \\\n"
            '           --user-data-dir="$HOME/Library/Application Support/MemoryB/douyin-reference-profile"\n'
            "       否则 memory-B 会退回 Playwright 持久 profile（很可能被抖音验证墙挡下）。" % cdp,
            file=sys.stderr,
        )
        return False
    return True


def fetch_douyin(args: argparse.Namespace) -> Any:
    mb = resolve_memory_b_dir(args.memory_b_dir)
    if not mb:
        raise SystemExit("未找到 memory-B 目录，请用 --memory-b-dir 指定。")
    npm = shutil.which("npm") or "npm"
    cmd = [
        npm, "--prefix", mb, "run", "reference:douyin", "--",
        "--topic", args.topic,
        "--lookback-days", str(args.reference_lookback_days),
        "--max-results", str(args.max_results),
        "--max-scrolls", str(args.max_scrolls),
    ]
    if args.keywords:
        cmd += ["--keywords", args.keywords]
    _check_cdp()
    print(f"[info] 实时抓取 memory-B：{' '.join(cmd)}", file=sys.stderr)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=540)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"运行 memory-B 抓取失败：{exc}")
    out = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    data = extract_json(out)
    if data is None:
        raise SystemExit("memory-B 抓取未返回可解析 JSON（可能遇到登录/验证码/限频停止）。")
    if isinstance(data, dict) and data.get("ok") is False:
        print(f"[warn] memory-B 返回状态 {data.get('status')}：{data.get('nextStep', '')}", file=sys.stderr)
    return data


def fetch_podcast(args: argparse.Namespace) -> Any:
    """Live-run memory-B douyin search, but targeted at 抖音播客/音频 content.

    Reuses the exact same `npm run reference:douyin` pipeline. The only
    differences are podcast-oriented keywords (so search surfaces audio/podcast
    clips) plus a lower like threshold and a wider lookback (podcasts publish
    less frequently than viral videos). The captured JSON is tagged
    platform=抖音播客 so the source table reads correctly.
    """
    mb = resolve_memory_b_dir(args.memory_b_dir)
    if not mb:
        raise SystemExit("未找到 memory-B 目录，请用 --memory-b-dir 指定。")
    npm = shutil.which("npm") or "npm"
    extra = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else []
    keywords = ",".join(extra + ["播客", "音频"])
    cmd = [
        npm, "--prefix", mb, "run", "reference:douyin", "--",
        "--topic", args.topic,
        "--keywords", keywords,
        "--lookback-days", str(args.podcast_lookback_days),
        "--min-likes", str(args.podcast_min_likes),
        "--max-results", str(args.max_results),
        "--max-scrolls", str(args.max_scrolls),
        "--out-dir", "logs/instant_reference_podcast",
    ]
    print(f"[info] 实时抓播客（memory-B）：{' '.join(cmd)}", file=sys.stderr)
    _check_cdp()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=540)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"运行 memory-B 播客抓取失败：{exc}")
    out = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    data = extract_json(out)
    if data is None:
        raise SystemExit("memory-B 播客抓取未返回可解析 JSON（可能遇到登录/验证码/限频停止）。")
    if isinstance(data, dict):
        data["platform"] = "抖音播客"
        if data.get("ok") is False:
            print(f"[warn] memory-B 返回状态 {data.get('status')}：{data.get('nextStep', '')}", file=sys.stderr)
    return data


def extract_json(text: str) -> Any | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# Source normalization (shared by all feed modes)
# ---------------------------------------------------------------------------
def parse_as_of(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_sources(raw: Any, as_of: date) -> list[Source]:
    if isinstance(raw, dict) and isinstance(raw.get("videos"), list):
        platform = raw.get("platform") or "抖音"
        generated_at = raw.get("generatedAt") or raw.get("generated_at") or ""
        return [
            normalize_source(
                {
                    "title": item.get("title") or item.get("cardTextPreview") or "未命名视频",
                    "speaker": item.get("speaker") or item.get("account") or item.get("keyword") or "待补人物",
                    "platform": platform,
                    "url": item.get("videoUrl"),
                    "published_at": item.get("publishTimeRaw") or item.get("published_at"),
                    "quote_summary": item.get("quote_summary") or summarize_card(item),
                    "relevance": item.get("relevance") or infer_relevance(item),
                    "likes": item.get("likeCountNumber"),
                    "generated_at": generated_at,
                },
                as_of,
            )
            for item in raw["videos"]
        ]
    if isinstance(raw, dict) and isinstance(raw.get("sources"), list):
        return [normalize_source(item, as_of) for item in raw["sources"]]
    if isinstance(raw, list):
        return [normalize_source(item, as_of) for item in raw]
    raise ValueError("Unsupported source JSON. Provide a list, {sources: [...]}, or Douyin {videos: [...]}.")


def normalize_source(item: dict[str, Any], as_of: date) -> Source:
    raw_time = first_text(
        item,
        "published_at",
        "publish_time",
        "publishTimeRaw",
        "publish_time_raw",
        "date",
        "generated_at",
    )
    parsed_date = parse_publish_date(raw_time, as_of)
    url = first_text(item, "url", "link", "source_url", "videoUrl", "video_url")
    quote_summary = first_text(item, "quote_summary", "original_summary", "summary", "cardTextPreview")
    if not quote_summary:
        quote_summary = "待补原话摘要"
    claimed_status = first_text(item, "verification_status", "verificationStatus", "status").lower()
    explicitly_verified = item.get("verified") is True or claimed_status in {"已核验", "verified"}
    status = (
        "已核验"
        if explicitly_verified
        and is_verifiable_url(url)
        and parsed_date
        and quote_summary != "待补原话摘要"
        else "待补核验"
    )
    return Source(
        title=first_text(item, "title", "name") or "未命名来源",
        speaker=first_text(item, "speaker", "person", "creator", "account", "author") or "待补人物",
        platform=first_text(item, "platform", "source_platform") or "待补平台",
        url=url or "待补链接",
        published_at=parsed_date.isoformat() if parsed_date else raw_time or "待补发布时间",
        published_date=parsed_date,
        quote_summary=quote_summary,
        relevance=first_text(item, "relevance", "why_it_matters") or infer_relevance(item),
        raw_time=raw_time or "",
        likes=parse_int(item.get("likes") or item.get("likeCountNumber") or item.get("like_count")),
        verification_status=status,
    )


def first_text(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def is_verifiable_url(raw: str) -> bool:
    if not raw:
        return False
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and bool(host) and host not in {
        "example.com",
        "www.example.com",
        "example.org",
        "www.example.org",
    }


def parse_publish_date(raw: str, as_of: date) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None
    iso = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", text)
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    md = re.search(r"(\d{1,2})[-/.月](\d{1,2})", text)
    if md:
        try:
            return date(as_of.year, int(md.group(1)), int(md.group(2)))
        except ValueError:
            return None
    if "今天" in text or "刚刚" in text:
        return as_of
    if "昨天" in text:
        return as_of - timedelta(days=1)
    if "前天" in text:
        return as_of - timedelta(days=2)
    days = re.search(r"(\d+)\s*天前", text)
    if days:
        return as_of - timedelta(days=int(days.group(1)))
    weeks = re.search(r"(\d+)\s*周前", text)
    if weeks:
        return as_of - timedelta(weeks=int(weeks.group(1)))
    months = re.search(r"(\d+)\s*个月前", text)
    if months:
        return as_of - timedelta(days=int(months.group(1)) * 30)
    years = re.search(r"(\d+)\s*年前", text)
    if years:
        return as_of - timedelta(days=int(years.group(1)) * 365)
    hours = re.search(r"(\d+)\s*小时", text)
    if hours:
        return as_of
    return None


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else None


def summarize_card(item: dict[str, Any]) -> str:
    text = str(item.get("cardTextPreview") or "").strip()
    if not text:
        return "待补原话摘要"
    return compact(text, 84)


def infer_relevance(item: dict[str, Any]) -> str:
    text = " ".join(str(v) for v in item.values() if isinstance(v, (str, int, float)))
    if any(word in text for word in ["AI", "人工智能", "智能体", "大模型", "Kimi"]):
        return "提供AI语境下工作与个体价值变化的讨论素材。"
    if any(word in text for word in ["工作", "职场", "自由", "价值", "个体"]):
        return "提供工作、自由与个体价值的情绪切口。"
    return "与本期主题存在潜在关联，需人工复核。"


def filter_sources(sources: list[Source], start: date, end: date) -> list[Source]:
    return [
        source
        for source in sources
        if source.published_date is not None and start <= source.published_date <= end
    ]


# ---------------------------------------------------------------------------
# LLM integration (stdlib urllib, no third-party deps)
# ---------------------------------------------------------------------------
def has_llm_key() -> bool:
    return bool(os.environ.get("LLM_API_KEY"))


def read_voice_guide() -> str:
    path = Path(__file__).resolve().parent.parent / "references" / "voice-and-format.md"
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


def call_llm(system_prompt: str, user_prompt: str) -> str | None:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return None
    base_url = os.environ.get("LLM_BASE_URL", "https://www.packyapi.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "claude-sonnet-5")
    fmt = os.environ.get("LLM_FORMAT", "openai_compatible")

    if fmt == "anthropic":
        url = f"{base_url}/v1/messages"
        body = {
            "model": model,
            "max_tokens": 8000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    else:
        url = f"{base_url}/chat/completions"
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"authorization": f"Bearer {api_key}", "content-type": "application/json"}

    req = urllib_request(url, body, headers)
    try:
        with urllib_request_opener(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] LLM 调用失败：{exc}；回退模板。", file=sys.stderr)
        return None

    if fmt == "anthropic":
        blocks = data.get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def urllib_request(url: str, body: dict, headers: dict):  # pragma: no cover - thin wrapper
    import urllib.request

    return urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")


def urllib_request_opener(req, timeout: int = 180):  # pragma: no cover - thin wrapper
    import urllib.request

    return urllib.request.urlopen(req, timeout=timeout)


def build_source_brief(sources: list[Source]) -> str:
    lines: list[str] = []
    for i, s in enumerate(sources, start=1):
        lines.append(f"#{i} 《{s.title}》— {s.speaker}（{s.platform}，{s.published_at}）")
        lines.append(f"原话摘要：{s.quote_summary}")
        lines.append(f"链接：{s.url}")
    return "\n".join(lines)


def generate_payload(topic: str, days: int, sources: list[Source], voice_text: str) -> dict | None:
    brief = build_source_brief(sources)
    system = (
        "你是短播客选题与稿件编辑，风格温和、敏感、清醒，把感受作为第一触角。"
        "受众是20-30岁小镇青年与白领，面对AI焦虑与意义疲劳。"
        "严禁卖焦虑、成功学、工具崇拜、命令式口吻（不用“你必须”）。\n\n"
    )
    if voice_text:
        system += f"以下是本工作流的内容风格与结构规范，必须严格遵守：\n{voice_text}\n"

    user = (
        f"本期主题：{topic}\n滚动窗口：最近{days}天\n\n"
        f"以下为已核验来源（编号用于稿件中的来源引用）：\n{brief}\n\n"
        "请严格输出一个 JSON 对象（不要使用 Markdown 代码块，直接输出 JSON）：\n"
        "{\n"
        '  "topics": [ {"title": str, "copy": str, "emotional_point": str, "hook": str,'
        ' "score": int(0-100), "source_refs": [str]} ],  # 恰好3个，按传播潜力50%+情绪共鸣50%打分\n'
        '  "best_topic_title": str,  # 三个选题中推荐写成5分钟稿的标题\n'
        '  "best_topic_reason": str,  # 1-2句话，说明为什么这个选题最适合做本期5分钟稿，必须紧扣本期主题与已核验来源，不要套用固定套路\n'
        '  "draft": str,  # 完整5分钟稿件，900-1200字，含[开场][来源引入][情绪翻译][观点展开][生活落点][结尾]六段标注，[来源引入]中引用来源编号如#1\n'
        '  "title_alternatives": [str, str, str, str],  # 4-5条\n'
        '  "release_intro": str,  # 发布简介1段\n'
        '  "comment_prompt": str,  # 评论区引导1句\n'
        '  "next_episode": [str, str, str]  # 3条下期延展\n'
        "}\n只输出JSON，不要任何解释。"
    )
    raw = call_llm(system, user)
    if not raw:
        return None
    return parse_llm_payload(raw)


def parse_llm_payload(raw: str) -> dict | None:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict) or "topics" not in data or "draft" not in data:
        return None
    if not isinstance(data["topics"], list) or len(data["topics"]) == 0:
        return None
    return data


def normalize_llm_topic(t: Any) -> dict:
    if not isinstance(t, dict):
        return {"title": "未命名选题", "copy": "", "emotional_point": "", "hook": "", "score": 0, "source_refs": []}
    refs = t.get("source_refs") or []
    refs = [f"#{str(r).lstrip('#')}" for r in refs]
    return {
        "title": str(t.get("title", "未命名选题")),
        "copy": str(t.get("copy", "")),
        "emotional_point": str(t.get("emotional_point", "")),
        "hook": str(t.get("hook", "")),
        "score": int(t.get("score", 0) or 0),
        "source_refs": refs,
    }


def topic_option_to_dict(t: TopicOption) -> dict:
    return {
        "title": t.title,
        "copy": t.copy,
        "emotional_point": t.emotional_point,
        "hook": t.hook,
        "score": t.score,
        "source_refs": [f"#{i}" for i in t.source_indexes],
    }


# ---------------------------------------------------------------------------
# Template fallback (original scaffold)
# ---------------------------------------------------------------------------
def build_topics(sources: list[Source], topic: str) -> list[TopicOption]:
    source_text = " ".join(f"{s.title} {s.quote_summary} {s.relevance}" for s in sources)
    has_ai = any(word in source_text for word in ["AI", "人工智能", "智能体", "大模型", "Kimi"])
    has_work = any(word in source_text for word in ["工作", "职场", "绩效", "效率", "岗位"])
    has_feeling = any(word in source_text for word in ["感受", "情绪", "精神", "自由", "意义", "内心"])
    base = 50 + (12 if has_ai else 0) + (10 if has_work else 0) + (12 if has_feeling else 0)
    options = [
        TopicOption(
            title="AI越会干活，人越要把感受放回第一位",
            copy="当所有人都在谈效率，我们想谈谈为什么感受仍然是人的第一触角。",
            emotional_point="年轻人不是只怕被替代，也怕自己越来越不知道什么让自己疼、什么让自己亮起来。",
            hook="AI时代，最稀缺的也许不是技能，而是你还愿意相信自己的感受。",
            score=min(96, base + 10),
            source_indexes=pick_source_indexes(sources, ["AI", "工作", "感受", "价值"]),
        ),
        TopicOption(
            title="别急着把自己当AI原生公司，先别把自己当机器",
            copy="个人可以学习AI工作流，但不必把整个人生都变成一套生产系统。",
            emotional_point="它接住的是精英白领和小镇青年共同的疲惫：越想变强，越容易把自己使用到枯竭。",
            hook="效率可以交给工具，但生活不能只剩优化。",
            score=min(94, base + 6),
            source_indexes=pick_source_indexes(sources, ["工作流", "公司", "效率", "个体"]),
        ),
        TopicOption(
            title="工作变轻以后，为什么我们的心更累了",
            copy="AI减少了一些劳动，却也让人更直接地面对意义、选择和自我怀疑。",
            emotional_point="很多焦虑并不来自任务太重，而是来自不知道自己还在为什么负责。",
            hook="当执行变便宜，人的内心秩序开始变贵。",
            score=min(92, base + 3),
            source_indexes=pick_source_indexes(sources, ["工作", "意义", "焦虑", "价值"]),
        ),
    ]
    return sorted(options, key=lambda item: item.score, reverse=True)


def pick_source_indexes(sources: list[Source], keywords: list[str]) -> list[int]:
    matches: list[int] = []
    for index, source in enumerate(sources, start=1):
        text = f"{source.title} {source.quote_summary} {source.relevance}"
        if any(keyword in text for keyword in keywords):
            matches.append(index)
        if len(matches) >= 3:
            break
    return matches or list(range(1, min(3, len(sources)) + 1))


def render_draft(best: TopicOption, sources: list[Source]) -> str:
    source_sentence = render_source_sentence(sources)
    return f"""[开场]
这两年我们一直在听一种声音：AI会更快，工具会更强，工作会被重新分配。可我最近更想问的是另一个问题：当一切都在变得有效率，我们还敢不敢相信自己的感受？

[来源引入]
最近几条可核验的访谈和视频里，都在反复碰到同一个主题：AI改变的不只是任务怎么完成，也改变了人怎么理解自己的价值。{source_sentence}这些讨论表面上在说技术和工作，往里看，其实是在问：人还剩下什么不能被外包？

[情绪翻译]
你可能也有过这种感觉。不是完全害怕AI，也不是不想学习新工具，而是某个瞬间突然发现，自己越来越像一个需要不断更新的系统。要更快回复，更快产出，更快证明自己有用。可是很少有人问：我舒服吗？我真的愿意吗？我心里那个很小的“不对劲”，有没有资格被听见？

[观点展开]
我想说，AI时代最容易被低估的能力，可能不是执行力，而是感受力。感受不是脆弱，也不是矫情。它是一个人最早的判断系统。你感到疲惫，可能是在提醒你某种节奏不适合你。你感到羡慕，可能是在提醒你有一种生活还没被允许。你对一份工作迟迟无法投入，也许不是你不够努力，而是你的内在秩序正在轻轻抗议。

当AI越来越会执行，人当然需要学习工具。但更重要的是，我们不能把自己也训练成工具。工具只问怎样更快，人还要问为什么要这样做。工具可以生成答案，人要辨认哪个答案和自己的生命有关。工具可以帮你写一段话，但它不能替你知道，哪一句话说出来的时候，你终于感觉自己回到了自己身上。

所以，个体价值也许正在换一种算法。过去我们常常用产量证明自己：我做了多少，我扛了多久，我有没有比别人更能忍。可是未来，真正珍贵的可能是：你能不能定义值得做的事，能不能保留自己的判断，能不能在很吵的世界里，仍然听见心里最细的一点声音。

[生活落点]
如果你最近也被AI和工作推着往前走，可以先不用急着给自己制定一个更狠的计划。你可以只做一件很小的事：每天记录一个感受，不解释，不评判，只写下来。今天什么让我紧了？什么让我亮了一下？什么让我想逃？什么让我想靠近？

这些感受不会立刻变成答案，但它们会慢慢把你带回自己。一个人真正的方向感，很多时候不是从宏大的目标开始，而是从一次诚实的感受开始。

[结尾]
AI会继续变强，工作也会继续变化。但愿我们不要只学会使用工具，也慢慢学会不把自己当成工具。下一次，当你心里出现一个很轻的“不对劲”，也许可以先别压下去。它可能正是你还活得很真实的证据。"""


def render_source_sentence(sources: list[Source]) -> str:
    verified = [s for s in sources if s.verification_status == "已核验"]
    selected = verified[:2] or sources[:2]
    if not selected:
        return "当前素材仍需补充来源核验。"
    fragments = []
    for source in selected:
        summary = compact(source.quote_summary, 42).rstrip("。；;")
        fragments.append(f"{source.speaker}在《{source.title}》中提到：{summary}")
    return "；".join(fragments) + "。"


def title_alternatives(best_title: str) -> list[str]:
    return [
        best_title,
        "AI时代，别急着变快，先听见自己",
        "当工具越来越强，感受为什么变得更重要",
        "你不是一套工作流，你是一个人",
        "AI不会替你知道，你真正想怎么生活",
    ]


def score_stars(score: int) -> str:
    if score >= 90:
        return "★★★★★"
    if score >= 80:
        return "★★★★☆"
    if score >= 70:
        return "★★★☆☆"
    return "★★☆☆☆"


# ---------------------------------------------------------------------------
# Report rendering (unified for LLM + template)
# ---------------------------------------------------------------------------
def render_report(
    topic: str,
    days: int,
    as_of: date,
    window_start: date,
    sources: list[Source],
    all_sources: list[Source],
    llm_payload: dict | None,
) -> str:
    active = sources or all_sources

    if llm_payload:
        topics = [normalize_llm_topic(t) for t in llm_payload.get("topics", [])]
        best_title = llm_payload.get("best_topic_title") or (topics[0]["title"] if topics else "")
        best = next((t for t in topics if t["title"] == best_title), topics[0]) if topics else None
        draft = (llm_payload.get("draft") or "").strip()
        title_alts = llm_payload.get("title_alternatives") or ([best["title"]] if best else [])
        release_intro = llm_payload.get("release_intro") or DEFAULT_RELEASE_INTRO
        comment_prompt = llm_payload.get("comment_prompt") or DEFAULT_COMMENT_PROMPT
        next_eps = llm_payload.get("next_episode") or list(DEFAULT_NEXT_EPISODE)
        mode = "生成式（LLM）"
    else:
        topics_obj = build_topics(active, topic)
        topics = [topic_option_to_dict(t) for t in topics_obj]
        best = topic_option_to_dict(topics_obj[0]) if topics_obj else None
        draft = render_draft(topics_obj[0], active) if topics_obj else ""
        title_alts = title_alternatives(best["title"]) if best else []
        release_intro = DEFAULT_RELEASE_INTRO
        comment_prompt = DEFAULT_COMMENT_PROMPT
        next_eps = list(DEFAULT_NEXT_EPISODE)
        mode = "模板回退"

    lines: list[str] = []
    lines.append(f"# 短播客工作流报告：{topic}")
    lines.append("")
    lines.append(f"- 生成日期：{as_of.isoformat()}")
    lines.append(f"- 滚动窗口：{window_start.isoformat()} 至 {as_of.isoformat()}（最近{days}天）")
    lines.append(f"- 生成模式：{mode}")
    lines.append("- 核心要义：个体精神世界富足，把感受作为第一触角。")
    if not sources:
        lines.append("- 核验提示：没有可解析为窗口内日期的素材，本报告使用全部输入素材生成草案，并保留待补核验标记。")
    lines.append("")

    lines.append("## 来源核验")
    lines.append("")
    lines.append("| # | 来源 | 人物/账号 | 平台 | 发布时间 | 原话摘要 | 核验状态 |")
    lines.append("|---|---|---|---|---|---|---|")
    for i, source in enumerate(active, start=1):
        source_link = f"[{escape_pipe(source.title)}]({source.url})" if source.url != "待补链接" else escape_pipe(source.title)
        lines.append(
            "| {i} | {source_link} | {speaker} | {platform} | {published_at} | {summary} | {status} |".format(
                i=i,
                source_link=source_link,
                speaker=escape_pipe(source.speaker),
                platform=escape_pipe(source.platform),
                published_at=escape_pipe(source.published_at),
                summary=escape_pipe(compact(source.quote_summary, 72)),
                status=source.verification_status,
            )
        )
    lines.append("")

    lines.append("## 3个选题")
    lines.append("")
    for i, option in enumerate(topics, start=1):
        source_refs = "、".join(option["source_refs"]) or "待补来源"
        recommend = "是" if best and option["title"] == best["title"] else "否"
        lines.append(f"### {i}. {option['title']}")
        lines.append("")
        lines.append(f"- 文案：{option['copy']}")
        lines.append(f"- 来源：{source_refs}")
        lines.append(f"- 情绪共鸣点：{option['emotional_point']}")
        lines.append(f"- 传播钩子：{option['hook']}")
        lines.append(f"- 推荐指数：{score_stars(option['score'])}（{option['score']}/100）")
        lines.append(f"- 是否建议写成5分钟稿：{recommend}")
        lines.append("")

    lines.append("## 最强选题")
    lines.append("")
    if best:
        lines.append(f"**{best['title']}**")
        lines.append("")
        if llm_payload:
            reason = (llm_payload.get("best_topic_reason") or "").strip()
            if not reason:
                reason = f"它最适合做成本期，因为紧扣「{topic}」主题，来源充分且情绪共鸣与传播潜力兼具。"
        else:
            reason = f"它最适合做成本期，因为紧扣「{topic}」主题，来源充分且情绪共鸣与传播潜力兼具。"
        if reason:
            lines.append(reason)
            lines.append("")

    lines.append("## 5分钟带标注初稿")
    lines.append("")
    lines.append(draft if draft else "（未生成稿件）")
    lines.append("")

    lines.append("## 标题备选")
    lines.append("")
    for title in title_alts:
        lines.append(f"- {title}")
    lines.append("")

    lines.append("## 发布简介")
    lines.append("")
    lines.append(release_intro or "（待补）")
    lines.append("")

    lines.append("## 评论区引导")
    lines.append("")
    lines.append(comment_prompt or "（待补）")
    lines.append("")

    lines.append("## 下期延展")
    lines.append("")
    for item in next_eps:
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def compact(text: str, limit: int) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def escape_pipe(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()
