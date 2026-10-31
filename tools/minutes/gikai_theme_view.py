#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


_DATE_RE = re.compile(
    r"令和(?P<reiwa>\d+)年（(?P<year>\d{4})年）(?P<month>\d+)月(?P<day>\d+)日"
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _is_speaker_line(line: str) -> bool:
    return line.startswith("○")


def _split_speaker_and_text(line: str) -> tuple[str, str]:
    s = line[1:]
    match = re.search(r"[ 　]{2,}", s)
    if not match:
        return s.strip(), ""
    speaker_part = s[: match.start()].strip()
    text_part = s[match.end() :].strip()
    return speaker_part, text_part


def _parse_speaker(speaker_part: str) -> dict[str, str]:
    speaker_part = speaker_part.strip()
    role_label = ""
    speaker_name = speaker_part
    speaker_title = ""

    m = re.match(r"^(?P<label>[^（(]+)[（(](?P<inside>[^)）]+)[)）]$", speaker_part)
    if m:
        role_label = m.group("label").strip()
        speaker_name = m.group("inside").strip()
        speaker_title = role_label
        return {
            "name": speaker_name,
            "title": speaker_title,
            "label": role_label,
        }

    chunks = [c for c in re.split(r"[ 　]+", speaker_part) if c]
    if len(chunks) >= 2:
        speaker_name = chunks[0]
        speaker_title = " ".join(chunks[1:])

    return {
        "name": speaker_name.strip(),
        "title": speaker_title.strip(),
        "label": role_label.strip(),
    }


def _speaker_type(speaker: dict[str, str]) -> str:
    label = speaker.get("label", "")
    title = speaker.get("title", "")
    name = speaker.get("name", "")
    if "議長" in label or "議長" in title or name.startswith("議長"):
        return "chair"
    if name.endswith("議員"):
        return "member"
    return "staff"


@dataclass
class Utterance:
    file_name: str
    meeting_date: str | None
    speaker: dict[str, str]
    speaker_type: str
    text: str
    start_line: int
    end_line: int


def _extract_meeting_date(lines: list[str]) -> str | None:
    for line in lines[:250]:
        match = _DATE_RE.search(line)
        if match:
            year = int(match.group("year"))
            month = int(match.group("month"))
            day = int(match.group("day"))
            return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def _iter_sections(all_lines: list[str]) -> Iterable[tuple[str, int, int]]:
    starts: list[tuple[str, int]] = []
    for index, line in enumerate(all_lines):
        if line.startswith("## ") and line.strip().endswith(".md"):
            name = line[3:].strip()
            starts.append((name, index))
    for i, (name, start_index) in enumerate(starts):
        end_index = starts[i + 1][1] if i + 1 < len(starts) else len(all_lines)
        yield name, start_index, end_index


def parse_utterances_from_merged(markdown_path: Path) -> list[Utterance]:
    all_lines = _read_text(markdown_path).splitlines()
    utterances: list[Utterance] = []

    for file_name, start_index, end_index in _iter_sections(all_lines):
        section_lines = all_lines[start_index:end_index]
        meeting_date = _extract_meeting_date(section_lines)

        current: dict[str, Any] | None = None
        for offset, line in enumerate(section_lines, start=start_index):
            line_no = offset + 1

            if _is_speaker_line(line):
                if current is not None:
                    utterances.append(
                        Utterance(
                            file_name=current["file_name"],
                            meeting_date=current["meeting_date"],
                            speaker=current["speaker"],
                            speaker_type=current["speaker_type"],
                            text="\n".join(current["text_lines"]).strip(),
                            start_line=current["start_line"],
                            end_line=current["end_line"],
                        )
                    )

                speaker_part, first_text = _split_speaker_and_text(line)
                speaker = _parse_speaker(speaker_part)
                stype = _speaker_type(speaker)
                current = {
                    "file_name": file_name,
                    "meeting_date": meeting_date,
                    "speaker": speaker,
                    "speaker_type": stype,
                    "text_lines": [first_text] if first_text else [],
                    "start_line": line_no,
                    "end_line": line_no,
                }
                continue

            if current is not None:
                current["text_lines"].append(line.rstrip())
                current["end_line"] = line_no

        if current is not None:
            utterances.append(
                Utterance(
                    file_name=current["file_name"],
                    meeting_date=current["meeting_date"],
                    speaker=current["speaker"],
                    speaker_type=current["speaker_type"],
                    text="\n".join(current["text_lines"]).strip(),
                    start_line=current["start_line"],
                    end_line=current["end_line"],
                )
            )

    utterances = [u for u in utterances if u.text.strip()]
    return utterances


def build_blocks_b(utterances: list[Utterance]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def close_current() -> None:
        nonlocal current
        if current is None:
            return
        current["end_line"] = current["utterances"][-1]["end_line"]
        blocks.append(current)
        current = None

    for u in utterances:
        if u.speaker_type == "member":
            questioner = u.speaker["name"]
            if current is None:
                current = {
                    "id": f"b{len(blocks)+1:04d}",
                    "questioner": questioner,
                    "meeting_date": u.meeting_date,
                    "file_name": u.file_name,
                    "start_line": u.start_line,
                    "end_line": u.end_line,
                    "utterances": [],
                }
            elif questioner != current["questioner"]:
                close_current()
                current = {
                    "id": f"b{len(blocks)+1:04d}",
                    "questioner": questioner,
                    "meeting_date": u.meeting_date,
                    "file_name": u.file_name,
                    "start_line": u.start_line,
                    "end_line": u.end_line,
                    "utterances": [],
                }

        if current is None:
            continue

        current["utterances"].append(
            {
                "speaker": u.speaker,
                "speaker_type": u.speaker_type,
                "text": u.text,
                "start_line": u.start_line,
                "end_line": u.end_line,
            }
        )

    close_current()
    return blocks


def load_theme_config(path: Path) -> list[dict[str, Any]]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, list):
        raise SystemExit("Theme config must be a JSON array.")
    for theme in config:
        if "id" not in theme or "title" not in theme or "keywords" not in theme:
            raise SystemExit("Each theme needs id/title/keywords.")
        if "min_score" in theme and not isinstance(theme["min_score"], int):
            raise SystemExit("Theme min_score must be an int if provided.")
    return config


def tag_blocks_with_themes(
    blocks: list[dict[str, Any]], themes: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_theme: dict[str, list[dict[str, Any]]] = {t["id"]: [] for t in themes}

    for block in blocks:
        scores: list[dict[str, Any]] = []
        for theme in themes:
            keywords = [kw for kw in theme["keywords"] if kw]
            all_hits: list[str] = []
            member_hits: list[str] = []
            for u in block["utterances"]:
                text = u.get("text", "")
                hits = [kw for kw in keywords if kw in text]
                if hits:
                    all_hits.extend(hits)
                    if u.get("speaker_type") == "member":
                        member_hits.extend(hits)

            uniq_all = sorted(set(all_hits), key=lambda x: all_hits.index(x))
            uniq_member = sorted(set(member_hits), key=lambda x: member_hits.index(x))
            if uniq_all:
                scores.append(
                    {
                        "id": theme["id"],
                        "score": len(uniq_all),
                        "member_score": len(uniq_member),
                        "hits": uniq_all[:30],
                        "member_hits": uniq_member[:30],
                    }
                )
        scores.sort(key=lambda x: x["score"], reverse=True)
        for i, s in enumerate(scores, start=1):
            s["rank"] = i
        block["themes"] = scores

        for s in scores:
            theme = next((t for t in themes if t["id"] == s["id"]), None)
            if theme is None:
                continue
            min_score = theme.get("min_score", 1)
            max_rank = theme.get("max_rank", 2)
            require_member_hit = theme.get("require_member_hit", True)

            if s["score"] < min_score:
                continue
            if isinstance(max_rank, int) and s.get("rank", 999) > max_rank:
                continue
            if require_member_hit and s.get("member_score", 0) < 1:
                continue

            by_theme[s["id"]].append({"block_id": block["id"], **s})

    return blocks, by_theme


def _filter_block_utterances_for_theme(
    block: dict[str, Any], theme: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    keywords = [kw for kw in theme.get("keywords", []) if kw]
    utterances = block.get("utterances", [])

    utterance_hits: dict[int, list[str]] = {}
    for i, u in enumerate(utterances):
        text = u.get("text", "")
        hits = [kw for kw in keywords if kw in text]
        if hits:
            uniq = sorted(set(hits), key=lambda x: hits.index(x))
            utterance_hits[i] = uniq[:30]

    if not utterance_hits:
        return [], []

    filtered: list[dict[str, Any]] = []
    all_hits: list[str] = []

    in_segment = False
    carry_remaining = 0
    for i, u in enumerate(utterances):
        speaker_type = u.get("speaker_type")
        matches = utterance_hits.get(i, [])
        text = u.get("text", "")

        if speaker_type == "member":
            in_segment = bool(matches)
            carry_remaining = 1 if in_segment else 0
            if in_segment:
                all_hits.extend(matches)
                filtered.append({**u, "theme_matches": matches})
            continue

        if in_segment:
            if matches:
                all_hits.extend(matches)
                filtered.append({**u, "theme_matches": matches})
                carry_remaining = 1
                continue

            if carry_remaining > 0 and len(text) <= 220:
                filtered.append({**u, "theme_matches": matches})
                carry_remaining -= 1

    uniq_all = sorted(set(all_hits), key=lambda x: all_hits.index(x))
    return filtered, uniq_all[:30]


def _auto_summary_ja(theme_title: str, block: dict[str, Any]) -> str:
    questioner = block.get("questioner", "")
    meeting_date = block.get("meeting_date", "")
    utterances = block.get("utterances", [])

    member = next((u for u in utterances if u.get("speaker_type") == "member"), None)
    staff = next((u for u in utterances if u.get("speaker_type") == "staff"), None)

    def first_sentences(text: str, max_sents: int = 2) -> str:
        t = re.sub(r"[ 　]+", " ", (text or "").replace("\n", " ")).strip()
        if not t:
            return ""
        parts = [p for p in re.split(r"(?<=。)", t) if p]
        joined = "".join(parts[:max_sents]).strip()
        if len(joined) > 140:
            joined = joined[:140].rstrip() + "…"
        return joined

    q = first_sentences(member.get("text", "") if member else "", 2)
    a = first_sentences(staff.get("text", "") if staff else "", 2)

    chunks: list[str] = []
    if meeting_date:
        chunks.append(f"{meeting_date}の議会で、")
    if questioner:
        chunks.append(f"{questioner}は")
    chunks.append(f"「{theme_title}」について質問しました。")
    if q:
        chunks.append(f"趣旨としては、{q}")
    if a:
        chunks.append(f"これに対し市側は、{a}")
    chunks.append("（※要約は暫定。確認は原文で）")

    s = "".join(chunks)
    if len(s) < 260:
        s += " どこが論点で、何が決まって（決まっていなくて）、市の説明の根拠は何か——を読み解く材料になります。"
    if len(s) > 420:
        s = s[:420].rstrip() + "…"
    return s


def load_summary_overrides(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("Summary overrides must be a JSON object.")
    out: dict[str, dict[str, str]] = {}
    for theme_id, v in data.items():
        if not isinstance(v, dict):
            continue
        out[theme_id] = {str(k): str(val) for k, val in v.items() if isinstance(val, str)}
    return out


def load_theme_explanations(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("Theme explanations must be a JSON object of {theme_id: summary}.")
    out: dict[str, str] = {}
    for theme_id, summary in data.items():
        if isinstance(summary, str) and summary.strip():
            out[str(theme_id)] = summary.strip()
    return out


def _block_heading(block: dict[str, Any]) -> str:
    for u in block["utterances"]:
        if u["speaker_type"] == "member":
            text = u["text"].replace("\n", " ").strip()
            if len(text) > 80:
                text = text[:80].rstrip() + "…"
            return text
    return ""


def build_theme_outputs(
    blocks: list[dict[str, Any]],
    themes: list[dict[str, Any]],
    by_theme: dict[str, list[dict[str, Any]]],
    summary_overrides: dict[str, dict[str, str]] | None = None,
    theme_explanations: dict[str, str] | None = None,
) -> dict[str, Any]:
    blocks_by_id = {b["id"]: b for b in blocks}

    theme_index: list[dict[str, Any]] = []
    per_theme_files: dict[str, dict[str, Any]] = {}

    summary_overrides = summary_overrides or {}
    theme_explanations = theme_explanations or {}

    for theme in themes:
        tid = theme["id"]
        scored = sorted(by_theme.get(tid, []), key=lambda x: x["score"], reverse=True)
        theme_blocks: list[dict[str, Any]] = []
        for s in scored:
            b = blocks_by_id[s["block_id"]]
            filtered_utterances, hits = _filter_block_utterances_for_theme(b, theme)
            if not filtered_utterances:
                continue

            block_for_theme = {
                "id": b["id"],
                "questioner": b["questioner"],
                "meeting_date": b.get("meeting_date"),
                "file_name": b.get("file_name"),
                "start_line": b.get("start_line"),
                "end_line": b.get("end_line"),
                "theme": {
                    "id": tid,
                    "score": s.get("score", 0),
                    "member_score": s.get("member_score", 0),
                    "rank": s.get("rank"),
                    "hits": hits,
                },
                "utterances": filtered_utterances,
            }

            override = summary_overrides.get(tid, {}).get(b["id"])
            block_for_theme["summary"] = (
                override.strip()
                if isinstance(override, str) and override.strip()
                else _auto_summary_ja(theme["title"], block_for_theme)
            )
            theme_blocks.append(block_for_theme)

        headings = []
        for b in theme_blocks[:20]:
            h = _block_heading(b)
            if h:
                headings.append(h)

        theme_summary = theme_explanations.get(tid, "").strip()
        theme_index.append(
            {
                "id": tid,
                "title": theme["title"],
                "description": theme.get("description", ""),
                "summary": theme_summary,
                "block_count": len(theme_blocks),
                "headings": headings[:10],
            }
        )

        per_theme_files[tid] = {
            "id": tid,
            "title": theme["title"],
            "description": theme.get("description", ""),
            "summary": theme_summary,
            "blocks": theme_blocks,
        }

    theme_index.sort(key=lambda x: x["block_count"], reverse=True)
    return {"themes": theme_index, "per_theme": per_theme_files}


def build_all(merged_path: Path, theme_config_path: Path, out_dir: Path) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    utterances = parse_utterances_from_merged(merged_path)
    blocks = build_blocks_b(utterances)
    themes = load_theme_config(theme_config_path)
    blocks, by_theme = tag_blocks_with_themes(blocks, themes)
    summary_overrides = load_summary_overrides(theme_config_path.parent / "theme_summaries.json")
    theme_explanations = load_theme_explanations(theme_config_path.parent / "theme_explanations.json")
    theme_outputs = build_theme_outputs(
        blocks,
        themes,
        by_theme,
        summary_overrides=summary_overrides,
        theme_explanations=theme_explanations,
    )

    _write_json(
        out_dir / "gikai_9_blocks.json",
        {
            "generated_at": generated_at,
            "source": str(merged_path),
            "block_unit": "B (質疑のまとまり: 質問者ごと)",
            "block_count": len(blocks),
            "blocks": blocks,
        },
    )
    _write_json(out_dir / "themes.json", {"generated_at": generated_at, **theme_outputs})

    themes_dir = out_dir / "themes"
    for tid, data in theme_outputs["per_theme"].items():
        _write_json(themes_dir / f"{tid}.json", {"generated_at": generated_at, **data})


def main() -> int:
    parser = argparse.ArgumentParser(description="Build NIHO gikai theme view data.")
    parser.add_argument(
        "--merged",
        default="NIHO/gikai/gikai_9.md",
        help="Merged minutes markdown path",
    )
    parser.add_argument(
        "--themes",
        default="NIHO/gikai/theme_keywords.json",
        help="Theme keyword config JSON path",
    )
    parser.add_argument(
        "--out-dir",
        default="NIHO/gikai/out",
        help="Output directory",
    )
    args = parser.parse_args()

    merged_path = Path(args.merged).resolve()
    theme_config_path = Path(args.themes).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not merged_path.exists():
        raise SystemExit(f"Missing merged file: {merged_path}")
    if not theme_config_path.exists():
        raise SystemExit(f"Missing theme config: {theme_config_path}")

    build_all(merged_path, theme_config_path, out_dir)
    print(f"Wrote: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
