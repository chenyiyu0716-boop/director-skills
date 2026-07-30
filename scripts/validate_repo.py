#!/usr/bin/env python3
"""Validate tracked skill package files without evaluating file names as code."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".sh", ".py", ".cjs", ".js"}
SECRET_PATTERNS = (
    re.compile(r"dev" + r"-director-[A-Za-z0-9_-]{4,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    )
    return [ROOT / item.decode() for item in output.split(b"\0") if item]


def run_check(command: list[str], path: Path) -> None:
    subprocess.run([*command, str(path)], cwd=ROOT, check=True)


def validate(path: Path) -> None:
    suffix = path.suffix.lower()
    relative = path.relative_to(ROOT)

    if suffix in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8")
        if relative != Path("scripts/validate_repo.py"):
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    raise ValueError(f"possible committed secret matching {pattern.pattern!r}")
    else:
        text = ""

    if suffix == ".json":
        json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        yaml.safe_load(text)
    elif suffix == ".sh":
        run_check(["bash", "-n"], path)
    elif suffix in {".cjs", ".js"}:
        run_check(["node", "--check"], path)
    elif suffix == ".py":
        compile(text, str(relative), "exec")

    if path.name == "SKILL.md":
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
        if not match:
            raise ValueError("missing YAML frontmatter")
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            raise ValueError("frontmatter must be a mapping")
        for key in ("name", "description"):
            if not frontmatter.get(key):
                raise ValueError(f"frontmatter missing {key}")


def main() -> int:
    failures: list[str] = []
    for path in tracked_files():
        if not path.is_file():
            continue
        try:
            validate(path)
        except Exception as exc:  # report all invalid files in one run
            failures.append(f"{path.relative_to(ROOT)}: {exc}")

    if failures:
        print("Repository validation failed:", file=sys.stderr)
        print("\n".join(f"- {failure}" for failure in failures), file=sys.stderr)
        return 1
    print("Repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
