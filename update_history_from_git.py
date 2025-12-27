#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


def _run(args: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(args, cwd=str(cwd), stderr=subprocess.STDOUT).decode("utf-8", "replace")


def _repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(50):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise SystemExit("Could not locate git repo root (no .git found). Run from inside the repo.")


AUTO_START = "<!-- HISTORY:AUTO:START -->"
AUTO_END = "<!-- HISTORY:AUTO:END -->"


@dataclass(frozen=True)
class Commit:
    sha: str
    date: str  # YYYY-MM-DD
    subject: str
    files: list[str]


def _parse_git_log(text: str) -> list[Commit]:
    commits: list[Commit] = []
    blocks = [b.strip("\n") for b in text.split("\n----\n") if b.strip()]
    for b in blocks:
        lines = [ln.rstrip("\n") for ln in b.splitlines()]
        if len(lines) < 4:
            continue
        sha = lines[0].strip()
        date = lines[1].strip()
        subject = lines[2].strip()
        files = []
        for ln in lines[3:]:
            s = ln.strip()
            if not s:
                continue
            # Defensive: ignore separators if they leak into the file list.
            if s == "----":
                continue
            files.append(s)
        commits.append(Commit(sha=sha, date=date, subject=subject, files=files))
    return commits


def _group_by_date(commits: list[Commit]) -> dict[str, list[Commit]]:
    grouped: dict[str, list[Commit]] = {}
    for c in commits:
        grouped.setdefault(c.date, []).append(c)
    return grouped


def _render_git_section(*, commits: list[Commit], rel_path: str, repo_root: Path) -> str:
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    out: list[str] = []
    out.append("## 自動追記（git log）")
    out.append("")
    out.append(f"- 対象パス: `{rel_path}`")
    out.append(f"- 生成時刻: `{generated_at}`")

    if not commits:
        out.append("")
        out.append("このパスに対するコミット履歴が見つかりませんでした。")
        out.append("")
        out.append("考えられる理由:")
        out.append(f"- `{rel_path}` がまだgitにコミットされていない（untracked / 未追加）")
        out.append("- 別ブランチで作業している")
        out.append("")
        out.append("現状の差分（working tree）サマリ:")
        try:
            status = _run(["git", "status", "--porcelain", "--", rel_path], cwd=repo_root).strip()
        except Exception as e:
            status = f"(git status failed: {e})"
        if not status:
            out.append("- 変更なし（git的にはクリーン）")
        else:
            lines = status.splitlines()
            added = sum(1 for ln in lines if ln.startswith("A ") or ln.startswith("?? "))
            modified = sum(1 for ln in lines if ln.startswith(" M") or ln.startswith("M "))
            deleted = sum(1 for ln in lines if ln.startswith(" D") or ln.startswith("D "))
            out.append(f"- 追加/未追跡: {added} 件 / 変更: {modified} 件 / 削除: {deleted} 件")
            out.append("- 詳細:")
            for ln in lines[:80]:
                out.append(f"  - `{ln}`")
            if len(lines) > 80:
                out.append(f"  - （他 {len(lines) - 80} 行省略）")
        out.append("")
        out.append("この自動追記を“履歴”として機能させるためのおすすめ:")
        out.append(f"- `git add {rel_path}` → `git commit -m \"init {rel_path}\"` で初回コミットしてから運用する")
        return "\n".join(out) + "\n"

    grouped = _group_by_date(commits)
    out.append(f"- 反映コミット数: {len(commits)}")
    out.append("")
    out.append("### 直近の変更（新しい順）")
    out.append("")

    for date in sorted(grouped.keys(), reverse=True):
        out.append(f"#### {date}")
        for c in grouped[date]:
            short = c.sha[:7]
            out.append(f"- `{short}` {c.subject}")
            for f in c.files:
                out.append(f"  - `{f}`")
        out.append("")

    return "\n".join(out) + "\n"


def _update_history_file(path: Path, new_block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if AUTO_START in text and AUTO_END in text:
        pre = text.split(AUTO_START, 1)[0]
        post = text.split(AUTO_END, 1)[1]
        updated = pre + AUTO_START + "\n" + new_block + AUTO_END + post
    else:
        updated = text.rstrip() + "\n\n" + AUTO_START + "\n" + new_block + AUTO_END + "\n"
    path.write_text(updated, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Append/replace an auto-generated git log section in history.md.")
    # This script now lives in the standalone `nihogov` repository, so defaults are repo-root relative.
    ap.add_argument("--path", default=".", help="Target path to summarize (default: .)")
    ap.add_argument("--history", default="history.md", help="History markdown file to update (default: history.md)")
    ap.add_argument("--max-commits", type=int, default=30, help="Max commits to include (default: 30)")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    repo_root = _repo_root(here)

    rel_path = args.path
    history_path = (repo_root / args.history).resolve()
    if not history_path.exists():
        raise SystemExit(f"history file not found: {history_path}")

    # Use date=short for stable grouping. Keep it minimal to avoid huge history.md.
    try:
        raw = _run(
            [
                "git",
                "log",
                f"-n{args.max_commits}",
                "--date=short",
                "--pretty=format:%H%n%ad%n%s%n",
                "--name-only",
                "--",
                rel_path,
            ],
            cwd=repo_root,
        )
    except Exception as e:
        raw = ""

    # Normalize into blocks separated by blank line between commits (git log outputs that).
    # We'll re-split by commit sha line.
    commits: list[Commit] = []
    if raw.strip():
        # Convert git output to our "----" separated format.
        chunks: list[str] = []
        current: list[str] = []
        for ln in raw.splitlines():
            if re.fullmatch(r"[0-9a-f]{40}", ln.strip()) and current:
                chunks.append("\n".join(current).strip() + "\n----")
                current = [ln]
            else:
                current.append(ln)
        if current:
            chunks.append("\n".join(current).strip() + "\n----")
        pseudo = "\n".join(chunks)
        commits = _parse_git_log(pseudo)

    new_block = _render_git_section(commits=commits, rel_path=rel_path, repo_root=repo_root)
    _update_history_file(history_path, new_block)
    print(f"Updated: {os.path.relpath(history_path, repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
