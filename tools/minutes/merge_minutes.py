#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def merge_minutes(files: list[Path], out_path: Path) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    header_lines = [
        "# 鎌倉市議会 9月定例会 会議録（統合）",
        "",
        "- 目的: 議事録データの「1つの参照元」を作る（機械的に連結）",
        f"- 生成: {now}",
        "- 元ファイル:",
        *[f"  - {p.name}" for p in files],
        "",
        "※注意: これは要約ではありません。内容の追加・削除はせず、区切り見出しだけ付けて連結しています。",
        "",
    ]

    parts: list[str] = ["\n".join(header_lines)]
    for path in files:
        parts.append("\n---\n")
        parts.append(f"## {path.name}\n")
        parts.append(_read_text(path).rstrip() + "\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(parts), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge Kamakura council minutes markdown files into a single file."
    )
    parser.add_argument(
        "--dir",
        default=str(Path(__file__).resolve().parent),
        help="Directory containing the minutes files (default: this script's directory)",
    )
    parser.add_argument(
        "--out",
        default="gikai_9.md",
        help="Output file name (default: gikai_9.md)",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Input file names in order (default: 0903..0930 in this folder)",
    )
    args = parser.parse_args()

    minutes_dir = Path(args.dir).expanduser().resolve()
    default_files = [
        "0903.md",
        "0904.md",
        "0905.md",
        "0908.md",
        "0909.md",
        "0910.md",
        "0911.md",
        "0930.md",
    ]

    file_names = args.files if args.files else default_files
    files = [minutes_dir / name for name in file_names]

    missing = [p for p in files if not p.exists()]
    if missing:
        missing_names = ", ".join(p.name for p in missing)
        raise SystemExit(f"Missing input files: {missing_names} (dir={minutes_dir})")

    out_path = minutes_dir / args.out
    merge_minutes(files, out_path)
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
