#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


def _pillow_installed() -> bool:
    try:
        import PIL  # noqa: F401

        return True
    except Exception:
        return False


def _in_git_repo(cwd: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode == 0 and proc.stdout.strip() == "true"
    except Exception:
        return False


def _top_level_summary(cwd: Path) -> list[str]:
    items = sorted([p for p in cwd.iterdir() if not p.name.startswith(".git")], key=lambda p: p.name.lower())
    lines: list[str] = []
    for p in items:
        kind = "dir" if p.is_dir() else "file"
        lines.append(f"- {p.name} ({kind})")
    return lines


def main() -> int:
    cwd = Path.cwd()
    print(f"OS: {platform.platform()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Working Directory: {cwd}")
    print(f"Pillow Installed: {str(_pillow_installed()).lower()}")
    print(f"Inside Git Repo: {str(_in_git_repo(cwd)).lower()}")
    print("Top-level Repo Entries:")
    for line in _top_level_summary(cwd):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
