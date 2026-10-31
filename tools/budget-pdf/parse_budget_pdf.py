#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import subprocess
import tempfile
from glob import glob
from typing import Any, Iterable


def _run(args: list[str]) -> str:
    return subprocess.check_output(args, stderr=subprocess.STDOUT).decode("utf-8", "replace")


def _parse_pages_arg(pages: str, max_pages: int | None) -> list[int]:
    pages = pages.strip()
    if pages.lower() in {"all", "*"}:
        if max_pages is None:
            raise SystemExit("--pages all requires knowing page count; pass --max-pages or rely on pdfinfo")
        return list(range(1, max_pages + 1))

    result: set[int] = set()
    for part in pages.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a)
            end = int(b)
            if end < start:
                start, end = end, start
            for p in range(start, end + 1):
                result.add(p)
        else:
            result.add(int(part))

    return sorted(result)


def _pdf_page_count(pdf_path: str) -> int | None:
    try:
        out = _run(["pdfinfo", pdf_path])
    except Exception:
        return None
    m = re.search(r"^Pages:\s+(\d+)\s*$", out, flags=re.MULTILINE)
    if not m:
        return None
    return int(m.group(1))


def _extract_text(pdf_path: str, first: int, last: int, layout: bool) -> list[str]:
    args = ["pdftotext"]
    if layout:
        args.append("-layout")
    args += ["-f", str(first), "-l", str(last), pdf_path, "-"]
    raw = _run(args)
    pages = raw.split("\f")

    expected = last - first + 1
    if len(pages) >= expected:
        pages = pages[:expected]
    else:
        pages += [""] * (expected - len(pages))
    return pages


def _ocr_page(
    pdf_path: str,
    page_number: int,
    *,
    lang: str,
    tessdata_dir: str | None,
    dpi: int,
) -> str:
    # Render a single page to PNG, then run tesseract.
    # Keep everything in a temp dir so no intermediate files pollute the repo.
    with tempfile.TemporaryDirectory() as tmp:
        prefix = os.path.join(tmp, f"page_{page_number}")
        _run(
            [
                "pdftoppm",
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-png",
                "-r",
                str(dpi),
                pdf_path,
                prefix,
            ]
        )
        candidates = sorted(glob(f"{prefix}-*.png"))
        if not candidates:
            raise RuntimeError(f"OCR render failed: no PNG produced for page {page_number}")
        # When using pdftoppm -l == -f, it still outputs with zero padding like -01.
        img_path = candidates[0]

        out_base = os.path.join(tmp, f"ocr_{page_number}")
        cmd = ["tesseract", img_path, out_base, "-l", lang]
        if tessdata_dir:
            cmd += ["--tessdata-dir", tessdata_dir]
        cmd += ["--psm", "6"]
        _run(cmd)
        txt_path = out_base + ".txt"
        with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def _is_decorative_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    # Page footer like "- 11 -"
    if re.fullmatch(r"-\s*\d+\s*-", s):
        return True
    if re.fullmatch(r"[rRー―︱贔﹇︳゜̲，\.\-–—\s]+", s):
        return True
    return False


def _clean_text_keep_structure(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    cleaned: list[str] = []
    for ln in lines:
        if _is_decorative_line(ln):
            continue
        cleaned.append(ln)
    return "\n".join(cleaned).strip()


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def _clean_project_name(name: str | None) -> str | None:
    if not name:
        return None
    s = str(name)
    # Cut off trailing junk that sometimes gets concatenated.
    s = re.split(r"(令和\s*\d+年度|該当\s*(?:ページ|ペジ|ペー?ジ)|【|（款）)", s)[0]
    # Remove bracket artifacts and common decorative glyphs
    s = re.sub(r"[【】\[\]（）()﹇﹈]", " ", s)
    s = re.sub(r"[rRー―︱贔﹇︳゜̲冒．]", " ", s)
    s = _collapse_spaces(s)

    # Strip leading noise tokens: numbers / roman I / pipes / punctuation.
    s = re.sub(r"^(?:\d+\s+)+", "", s)
    s = re.sub(r"^(?:I|l|\||￨|︱)\s*", "", s)
    s = re.sub(r"^[︑｀`’'、，,。・\-–—ー]+\s*", "", s)
    s = _collapse_spaces(s)

    # If it still starts with a lone digit followed by space, drop it.
    s = re.sub(r"^\d\s+", "", s)
    s = _collapse_spaces(s)
    return s or None


def _normalize_prev_year_token(s: str) -> str:
    s = _collapse_spaces(s)
    # Common OCR / pdftotext confusions
    s = s.replace("〜", "～").replace("~", "～")
    # P + l/I confusion seen in some PDFs
    s = re.sub(r"([Pp])", "P", s)
    s = s.replace("Pl", "P1").replace("PI", "P1").replace("Pll", "P11")
    s = s.replace("l", "1").replace("I", "1")
    # Join split tokens like 'P 31' -> 'P31'
    s = re.sub(r"\bP\s+(\d{1,4})\b", r"P\1", s)
    return s.strip()


def _parse_prev_year_page(text: str) -> str | None:
    """
    Extract '令和X年度該当ページ： P31' while handling cases where 'P' and digits are split across lines.
    """
    lines = [ln.rstrip() for ln in text.splitlines()]
    for i, ln in enumerate(lines):
        if not re.search(r"該当\s*(?:ページ|ペジ|ペー?ジ)", ln):
            continue
        # Capture everything after ':' or '：'
        m = re.search(r"該当\s*(?:ページ|ペジ|ペー?ジ)\s*[：:]?\s*(.*)$", ln)
        tail = m.group(1) if m else ""
        tokens: list[str] = []
        if tail.strip():
            tokens.append(tail.strip())
        # Append subsequent numeric-only lines (common split: 'P' then '31')
        for j in range(i + 1, min(i + 6, len(lines))):
            nxt = lines[j].strip()
            if not nxt:
                continue
            if nxt.startswith("【") or nxt.startswith("（") or "【総合計画" in nxt:
                break
            if (
                re.fullmatch(r"[Pp]", nxt)
                or re.fullmatch(r"\d{1,4}", nxt)
                or re.fullmatch(r"[Pp]\d{1,4}", nxt)
                or re.fullmatch(r"[lI]\d{1,4}", nxt)
            ):
                tokens.append(nxt)
                continue
            # Sometimes split like 'P37 P38' on next line – allow if it contains P + digits
            if re.fullmatch(r"[Pp]\d{1,4}(?:\s+[Pp]\d{1,4})+", nxt):
                tokens.append(nxt)
            break
        joined = _normalize_prev_year_token(" ".join(tokens))
        return joined or None
    return None


def _parse_header(text: str) -> dict[str, Any]:
    flat = _collapse_spaces(text)
    header: dict[str, Any] = {}

    m = re.search(
        r"（\s*款\s*）\s*(\d+)\s*([^（]+?)\s*（\s*項\s*）\s*(\d+)\s*([^（]+?)\s*（\s*目\s*）\s*(\d+)\s*([^\n]+?)\s*(?:◎|$)",
        flat,
    )
    if m:
        header["category"] = {
            "kuan": {"code": int(m.group(1)), "name": m.group(2).strip()},
            "kou": {"code": int(m.group(3)), "name": m.group(4).strip()},
            "moku": {"code": int(m.group(5)), "name": m.group(6).strip()},
        }

    m = re.search(r"◎\s*([^\s]+)\s*[0○●]\s*([^\s]+)", flat)
    if m:
        header["field"] = m.group(1).strip()
        header["policy"] = m.group(2).strip()

    prev = _parse_prev_year_page(text)
    if prev:
        header["prev_year_page"] = prev

    return header


def _parse_name_department(text: str) -> tuple[str | None, str | None]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    def looks_like_dept(s: str) -> bool:
        return bool(re.search(r"(課|局|部|室|センター|事務所)", s))

    def normalize_dept(s: str | None) -> str | None:
        if not s:
            return None
        # Remove bracket artifacts and stray markers
        s = re.sub(r"[【】\[\]（）()]", " ", s)
        s = re.sub(r"[rRー―︱贔﹇︳゜̲冒．]", " ", s)
        s = re.sub(r"\b\d+\b", " ", s)
        s = _collapse_spaces(s)
        if not s:
            return None
        # If it's still just punctuation-like, drop it
        if re.fullmatch(r"[-–—ー]+", s):
            return None
        return s

    def normalize_name(s: str | None) -> str | None:
        if not s:
            return None
        s = re.sub(r"[rRー―︱贔﹇︳゜̲冒．]", " ", s)
        s = _collapse_spaces(s)
        return s or None

    # Prefer extracting from the "project name + 【department】" line; the PDF often splits the closing bracket.
    for i in range(len(lines)):
        if "◎" not in lines[i]:
            continue
        # Join a few subsequent lines to reconstruct '...【 ... 】'
        buf: list[str] = []
        for j in range(i + 1, min(i + 4, len(lines))):
            buf.append(lines[j])
            joined = _collapse_spaces(" ".join(buf))
            m = re.search(r"^(?P<name>.+?)\s*【\s*(?P<dept>.+?)\s*】", joined)
            if m:
                name = normalize_name(m.group("name"))
                dept = normalize_dept(m.group("dept"))
                # Avoid matching section headers like "【対象となる職員】" as the department.
                if dept and not looks_like_dept(dept):
                    continue
                if dept and ("対象となる職員" in dept or "令和" in dept or "該当" in dept):
                    continue
                if name and ("令和" in name or "該当" in name):
                    continue
                if name:
                    return name, dept

    limit = len(lines)
    for i, ln in enumerate(lines):
        if "令和" in ln and "該当ページ" in ln:
            limit = i
            break

    candidates = lines[:limit]

    # Salary pages often have the name on its own line (e.g. "職員給与費") and the department on the next line
    # with only a trailing closing bracket (e.g. "職員課 】"). Prefer this pattern when detected.
    for idx, ln in enumerate(candidates):
        if "給与費" not in ln:
            continue
        # Ignore header-like lines
        if "（款" in ln or "◎" in ln:
            continue
        # Pattern: '会計年度任用職員給与費 【 職員課・教育総務課' (opening bracket without closing)
        if "【" in ln and "】" not in ln:
            before, after = ln.split("【", 1)
            name = normalize_name(before)
            dept = normalize_dept(after)
            if dept and not looks_like_dept(dept):
                dept = None
            if name:
                return name, dept
        # Common case: the line already contains both name and department as separate columns.
        if re.search(r"\s{2,}", ln):
            parts = [p.strip() for p in re.split(r"\s{2,}", ln) if p.strip()]
            if len(parts) >= 2:
                dept_part = None
                for cand in parts[1:]:
                    if looks_like_dept(cand):
                        dept_part = cand
                        break
                if dept_part:
                    name = normalize_name(parts[0])
                    dept = normalize_dept(dept_part)
                    if name:
                        return name, dept
        name = normalize_name(ln)
        if not name:
            continue
        # Find a department-like line after this
        for j in range(idx + 1, min(idx + 8, len(candidates))):
            dln = candidates[j]
            if "令和" in dln and "該当ページ" in dln:
                break
            if looks_like_dept(dln):
                dept = normalize_dept(dln)
                if dept:
                    return name, dept

    best_line: str | None = None
    for ln in candidates:
        if "（款" in ln or "◎" in ln:
            continue
        if looks_like_dept(ln):
            best_line = ln
            break

    if best_line is None and candidates:
        best_line = candidates[-1]

    if not best_line:
        return None, None
    if re.fullmatch(r"\d{1,3}", best_line.strip()):
        return None, None

    parts = [p.strip() for p in re.split(r"\s{2,}", best_line) if p.strip()]
    if len(parts) >= 2:
        name = normalize_name(parts[0])
        dept = normalize_dept(parts[-1])
        # If dept is garbage (e.g. '】') and name itself looks like a department (e.g. '職員課'),
        # try to recover the actual project name from nearby candidates (e.g. '職員給与費').
        if dept is None and name and looks_like_dept(name):
            for ln in candidates:
                if "給与費" in ln and "（款" not in ln and "◎" not in ln:
                    recovered = normalize_name(ln)
                    if recovered:
                        return recovered, normalize_dept(name)
        return name, dept

    # Fallback: split by last department-like token
    m = re.search(r"(.+?)\s+((?:[^\\s]+?(?:課|局|部|室|センター|事務所))(?:[・、/][^\\s]+?(?:課|局|部|室|センター|事務所))*)$", best_line)
    if m:
        return normalize_name(m.group(1)), normalize_dept(m.group(2))

    return normalize_name(best_line), None


def _extract_block(text: str, start_marker: str, end_markers: Iterable[str]) -> str | None:
    start = text.find(start_marker)
    if start < 0:
        return None
    start += len(start_marker)
    end = len(text)
    for em in end_markers:
        p = text.find(em, start)
        if p >= 0:
            end = min(end, p)
    block = text[start:end].strip()
    return block or None


def _extract_block_by_header(text: str, header_label: str) -> str | None:
    """
    Extract a section like '【 事業の目的 】 ...' while tolerating whitespace differences.
    The end is the next '【' header or end-of-text.
    """
    pattern = rf"【\s*{re.escape(header_label)}\s*】"
    m = re.search(pattern, text)
    if not m:
        return None
    start = m.end()
    m2 = re.search(r"【", text[start:])
    end = start + m2.start() if m2 else len(text)
    block = text[start:end].strip()
    return block or None


def _parse_purpose(text: str) -> dict[str, str]:
    purpose: dict[str, str] = {}
    block = _extract_block_by_header(text, "事業の目的")
    if not block:
        return purpose

    for key in ("対象", "意図", "効果"):
        m = re.search(rf"^{key}\s*(.+)$", block, flags=re.MULTILINE)
        if m:
            purpose_key = {"対象": "target", "意図": "intent", "効果": "effect"}[key]
            purpose[purpose_key] = m.group(1).strip()
    return purpose


def _parse_description(text: str) -> list[str]:
    block = _extract_block_by_header(text, "事業の内容")
    if not block:
        return []

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    items: list[str] = []
    current: str | None = None
    for ln in lines:
        if ln.startswith("・") or ln.startswith("•"):
            if current:
                items.append(current)
            current = ln.lstrip("・•").strip()
            continue
        if ln.startswith("【"):
            break
        if current is None:
            current = ln
        else:
            # Continuation line (e.g., wrapped)
            current = f"{current}{ln}"
    if current:
        items.append(current)
    return items


def _parse_budget_heuristic(text: str) -> dict[str, Any]:
    unit = "千円" if "（単位：千円）" in text else None

    def normalize_int_token(token: str) -> int | None:
        s = re.sub(r"\s+", "", token)
        s = re.sub(r"[^0-9,\.]", "", s)
        if not s:
            return None
        # Some PDFs yield "24.31" + "0" (dot used as comma-ish separator)
        if "." in s and "," not in s and re.fullmatch(r"\d{1,3}\.\d{2,3}\d*", s):
            s = s.replace(".", ",", 1)
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+", s):
            return int(s.replace(",", ""))
        if re.fullmatch(r"\d+", s):
            return int(s)
        return None

    def extract_budget_table_lines(text_: str) -> tuple[list[str], str | None]:
        """
        Extract the (単位：千円) table region lines, up to (but excluding) the 予算内訳 marker.

        Keep per-line horizontal positions (indentation) so we can reconstruct vertically stacked
        digits per column without merging across columns (e.g. '1' + '71' vs '17' + '1').
        """
        lines = [ln.rstrip("\n") for ln in text_.splitlines()]
        start = None
        for i, ln in enumerate(lines):
            if "（単位：千円）" in ln:
                start = i
                break
        if start is None:
            for i, ln in enumerate(lines):
                if "事業費" in ln and "千円" in ln:
                    start = i
                    break
        if start is None:
            return ([], None)

        end = None
        for j in range(start + 1, min(start + 25, len(lines))):
            if "く予算内" in lines[j] or "＜予算内訳＞" in lines[j] or "<予算内訳>" in lines[j]:
                end = j
                break
        if end is None:
            end = min(start + 25, len(lines))

        header_line = None
        for j in range(start, end):
            if "一般財源" in lines[j]:
                header_line = lines[j]
                break

        return (lines[start:end], header_line)

    @dataclasses.dataclass
    class _PosTok:
        x: int
        row: int
        raw: str

    def extract_numbers_by_column(table_lines: list[str]) -> dict[int, int]:
        """
        Return {column_center_x: value} by clustering numeric tokens by x-position and
        concatenating vertically split digits within each column.
        """
        tokens: list[_PosTok] = []
        for row, ln in enumerate(table_lines):
            # Skip header-ish lines that contain labels but no numbers
            if "国県支出金" in ln or "地方債" in ln or "一般財源" in ln:
                continue
            for m in re.finditer(r"[0-9][0-9,\.IlI￨|]*", ln):
                raw = m.group(0)
                if normalize_int_token(raw) is None:
                    continue
                tokens.append(_PosTok(x=m.start(), row=row, raw=raw))

        if not tokens:
            return {}

        tokens_sorted = sorted(tokens, key=lambda t: t.x)
        clusters: list[dict[str, Any]] = []
        tol = 3
        for t in tokens_sorted:
            placed = False
            for c in clusters:
                if abs(t.x - c["center"]) <= tol:
                    c["tokens"].append(t)
                    c["center"] = (c["center"] * (len(c["tokens"]) - 1) + t.x) / len(c["tokens"])
                    placed = True
                    break
            if not placed:
                clusters.append({"center": float(t.x), "tokens": [t]})

        results: dict[int, int] = {}
        for c in clusters:
            center = int(round(c["center"]))
            col_tokens: list[_PosTok] = sorted(c["tokens"], key=lambda t: t.row)

            digit_fragments: list[str] = []
            for t in col_tokens:
                frag = re.sub(r"[^0-9,\.]", "", t.raw)
                if not frag:
                    continue
                # If we see a comma/dot separated number, treat it as a whole value.
                if re.fullmatch(r"\d{1,3}(?:,\d{3})+", frag):
                    digit_fragments = [frag]
                    break
                if re.fullmatch(r"\d{1,3}\.\d{3}", frag):
                    digit_fragments = [frag]
                    break
                digit_fragments.append(re.sub(r"[^0-9]", "", frag))

            joined = "".join(digit_fragments).strip()
            if not joined:
                continue
            if len(joined) > 9:
                continue
            val = normalize_int_token(joined)
            if val is None:
                continue
            results[center] = val

        return results

    table_lines, header_line = extract_budget_table_lines(text)
    cols = extract_numbers_by_column(table_lines) if table_lines else {}
    if not cols:
        return {"unit": unit, "total": None, "revenue": {}}

    sorted_cols = sorted(cols.items(), key=lambda kv: kv[0])
    total = sorted_cols[0][1]

    revenue: dict[str, Any] = {}
    if header_line and "一般財源" in header_line:
        general_x = header_line.find("一般財源")
        best = min(sorted_cols, key=lambda kv: abs(kv[0] - general_x))
        revenue["general"] = best[1]

    return {
        "unit": unit,
        "total": total,
        "revenue": revenue,
        "heuristic": {"table_columns": [{"x": x, "value": v} for x, v in sorted_cols]},
    }


def _looks_like_amount_only(line: str) -> int | None:
    s = line.strip()
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", s):
        return int(s.replace(",", ""))
    if re.fullmatch(r"\d+", s):
        return int(s)
    return None


def _parse_budget_details(text: str) -> list[dict[str, Any]]:
    # PDFs sometimes garble this marker (e.g., "く予算内宦ー→"), so match loosely.
    markers = ["く予算内訳", "＜予算内訳＞", "<予算内訳>", "く予算内"]
    start = -1
    marker_len = 0
    for mk in markers:
        p = text.find(mk)
        if p >= 0 and (start < 0 or p < start):
            start = p
            marker_len = len(mk)

    if start < 0:
        # Fallback 1: marker without the leading 'く' (OCR often yields plain "予算内訳")
        m = re.search(r"予算内訳", text)
        if m:
            start = m.start()
            marker_len = len("予算内訳")
        else:
            # Fallback 2: no marker at all, but section lines exist after "事業費"
            base = text.find("事業費")
            tail = text[base:] if base >= 0 else text
            m2 = re.search(r"^\s*\d+\s*節", tail, flags=re.MULTILINE)
            if not m2:
                return []
            start = (base if base >= 0 else 0) + m2.start()
            marker_len = 0

    block = text[start + marker_len :].strip()
    # Stop at footer page number like "- 11 -" if present
    block = re.split(r"\n\s*-\s*\d+\s*-\s*\n", block)[0].strip()

    lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
    details: list[dict[str, Any]] = []

    current_section: int | None = None
    pending_label: dict[str, Any] | None = None
    pending_amount_fragments: list[str] = []
    section_prefix_digit: str | None = None
    seen_any_section = False

    def is_skippable_line(s: str) -> bool:
        if "→" in s and "節" not in s:
            return True
        if re.fullmatch(r"[＞>,，。、\.]+", s.strip()):
            return True
        if "予算内訳" in s and "節" not in s:
            return True
        return False

    def next_significant_line(start_index: int) -> str | None:
        for j in range(start_index + 1, len(lines)):
            candidate = lines[j]
            if not candidate.strip():
                continue
            if is_skippable_line(candidate):
                continue
            return candidate
        return None

    def next_significant_line_after(start_index: int) -> str | None:
        """
        Like next_significant_line, but starts searching from the line after the found line.
        """
        first = None
        for j in range(start_index + 1, len(lines)):
            candidate = lines[j]
            if not candidate.strip():
                continue
            if is_skippable_line(candidate):
                continue
            first = j
            break
        if first is None:
            return None
        for k in range(first + 1, len(lines)):
            candidate = lines[k]
            if not candidate.strip():
                continue
            if is_skippable_line(candidate):
                continue
            return candidate
        return None

    for idx, ln in enumerate(lines):
        lead = len(ln) - len(ln.lstrip(" "))
        if ln.strip().startswith("【"):
            break
        if is_skippable_line(ln):
            continue
        # In some pages, a number appears before any section label (noise). Ignore amount-like lines
        # (heavily indented) until we see the first '節'. But keep low-indented digit lines as they
        # can be section-prefix digits ("1" + "4節" -> "14節").
        if not seen_any_section and re.fullmatch(r"\d{1,4}", ln.strip()) and lead >= 10:
            continue

        if pending_label is None and re.fullmatch(r"\d{1,3}", ln.strip()):
            # Decide whether this digit-only line is a section-prefix or just stray amount-like noise.
            nxt = next_significant_line(idx)
            if lead <= 4 and nxt is not None and re.search(r"^\d+\s*節", nxt.strip()):
                section_prefix_digit = ln.strip()
                continue
            # If it's far-right aligned, it is not a section prefix; ignore.
            if lead >= 10:
                continue
            # Otherwise, keep as a weak prefix candidate.
            section_prefix_digit = ln.strip()
            continue

        if pending_label is not None:
            # Some pages include a "数量" column before amount, often as a lone "1" on the same line:
            # e.g. "1        2,103". Do not concatenate these into "12,103".
            m_qty_amt = re.fullmatch(r"\s*(?P<qty>\d+)\s+(?P<amt>\d{1,3}(?:,\d{3})+|\d+)\s*", ln)
            if m_qty_amt:
                qty = m_qty_amt.group("qty")
                amt_token = m_qty_amt.group("amt")
                try:
                    amt = int(amt_token.replace(",", ""))
                except Exception:
                    amt = None
                if amt is not None:
                    if "quantity" not in pending_label and qty != "0":
                        pending_label["quantity"] = qty
                    # If the amount is split across lines like "2" + ",800", keep pending and join.
                    nxt = next_significant_line(idx)
                    if nxt is not None and nxt.strip().startswith(","):
                        pending_amount_fragments = [amt_token]
                        continue
                    pending_label["amount"] = amt
                    details.append(pending_label)
                    pending_label = None
                    pending_amount_fragments = []
                    continue

            # Amount may be split across multiple lines: "5" + ",647" -> "5,647"
            frag = ln.strip().replace(" ", "")
            if re.fullmatch(r"[0-9,]{1,6}", frag):
                pending_amount_fragments.append(frag)
                joined = "".join(pending_amount_fragments)
                if re.fullmatch(r"\d{1,3}(?:,\d{3})+", joined):
                    pending_label["amount"] = int(joined.replace(",", ""))
                    details.append(pending_label)
                    pending_label = None
                    pending_amount_fragments = []
                elif re.fullmatch(r"\d+", joined):
                    pending_label["amount"] = int(joined)
                    details.append(pending_label)
                    pending_label = None
                    pending_amount_fragments = []
                continue

            amount_only = _looks_like_amount_only(ln)
            if amount_only is not None:
                pending_label["amount"] = amount_only
                details.append(pending_label)
                pending_label = None
                pending_amount_fragments = []
                continue
            # Not an amount continuation; drop the pending label and parse this line as a new label.
            pending_label = None
            pending_amount_fragments = []

        m = re.search(r"(?P<label>.+?)\s+(?P<amount>\d{1,3}(?:,\d{3})+|\d+)$", ln.strip())
        if m:
            label = m.group("label").strip()
            amount_token = m.group("amount")
            amount = int(amount_token.replace(",", ""))
        else:
            label = ln.strip()
            amount = None
        # Handle partial amount fragments that remain on the label line, e.g. "... 1," then next line "000".
        partial_amount_fragment = None
        if amount is None:
            mfrag = re.search(r"^(?P<label>.+?)\s+(?P<frag>\d{1,3},)\s*$", label)
            if mfrag:
                label = mfrag.group("label").strip()
                partial_amount_fragment = mfrag.group("frag")

        m2 = re.match(r"^(?P<section>\d+)\s*節\s*(?P<rest>.+)$", label)
        if m2:
            seen_any_section = True
            section_text = m2.group("section")
            section_num = int(section_text)
            if (
                section_prefix_digit is not None
                and len(section_text) == 1
                and 0 <= section_num <= 9
                and re.fullmatch(r"\d", section_prefix_digit)
            ):
                combined = int(f"{section_prefix_digit}{section_text}")
                # Only accept plausible section numbers like 10-19 in this document style.
                if 10 <= combined <= 99:
                    section_num = combined
            elif section_prefix_digit is None and current_section is not None and current_section >= 10 and len(section_text) == 1:
                # When a leading digit of the section is split onto its own line but got consumed
                # as the previous row's amount, we may end up seeing "4節" instead of "14節".
                # In this budget format, sections commonly proceed in ascending order.
                candidate = (current_section // 10) * 10 + section_num
                if candidate > current_section and 10 <= candidate <= 99:
                    section_num = candidate
            current_section = section_num
            section_prefix_digit = None
            label = m2.group("rest").strip()
        else:
            section_prefix_digit = None

        quantity = None
        m3 = re.search(r"(?P<item>.+?)\s+(?P<qty>\d+\s*人)\s*$", label)
        if m3:
            label = m3.group("item").strip()
            quantity = m3.group("qty").replace(" ", "")

        entry: dict[str, Any] = {"section": current_section, "item": label}
        if quantity:
            entry["quantity"] = quantity

        if amount is None:
            pending_label = entry
            if partial_amount_fragment:
                pending_amount_fragments = [partial_amount_fragment]
            continue

        # If amount is a small prefix and the next significant line begins with a comma fragment,
        # treat this as a split number like "5" + ",647" (common in these PDFs).
        if re.fullmatch(r"\d{1,3}", str(amount)) and 1 <= amount <= 999:
            nxt = next_significant_line(idx)
            if nxt is not None and nxt.strip().startswith(","):
                pending_label = entry
                pending_amount_fragments = [str(amount)]
                continue
            # Another common split: last digit on the next line, e.g. "57" + "2" -> "572"
            if nxt is not None and re.fullmatch(r"\d", nxt.strip()) and 10 <= amount <= 99:
                # Guard: if the digit is actually a section-prefix digit (next line is like '1節 ...'),
                # do not treat it as an amount continuation.
                nxt2 = next_significant_line_after(idx)
                if nxt2 is None or not re.search(r"^\d+\s*節", nxt2.strip()):
                    pending_label = entry
                    pending_amount_fragments = [str(amount)]
                    continue
            # Another split: leading digit then a comma-number, e.g. "1" + "37,952" -> "137,952"
            if nxt is not None and re.fullmatch(r"\d", str(amount)) and re.search(r"\d{1,3},\d{3}", nxt):
                pending_label = entry
                pending_amount_fragments = [str(amount)]
                continue
            # Another split: leading digit then 2-3 digits, e.g. "1" + "24" -> "124"
            if nxt is not None and re.fullmatch(r"\d", str(amount)) and re.fullmatch(r"\d{2,3}", nxt.strip()):
                pending_label = entry
                pending_amount_fragments = [str(amount)]
                continue

        entry["amount"] = amount
        details.append(entry)

    # Keep trailing entry if its amount is missing (we can optionally fill later from total).
    if pending_label is not None:
        pending_label["amount"] = None
        details.append(pending_label)

    return details


def _quality_flags(page: dict[str, Any]) -> list[str]:
    parsed = page.get("parsed") or {}
    flags: list[str] = []

    name = parsed.get("name")
    if not name or re.fullmatch(r"[】\[\]（）()]+", re.sub(r"\s+", "", str(name))):
        flags.append("missing_or_bad_name")
    if not parsed.get("department"):
        flags.append("missing_department")
    prev = parsed.get("prev_year_page")
    if prev in (None, "", "P"):
        flags.append("prev_year_incomplete")

    budget = parsed.get("budget") or {}
    budget_total = budget.get("total")
    if budget_total is None:
        flags.append("missing_budget_total")
    if budget.get("mismatch_total_vs_details"):
        flags.append("total_mismatch_details")
    if budget.get("mismatch_general_vs_details"):
        flags.append("general_mismatch_details")
    if budget.get("total_display_source") in {"details_sum", "details_sum_weak", "general"}:
        flags.append("total_display_is_fallback")

    if name and _clean_project_name(name) != name:
        flags.append("suspicious_name")

    # Amount sanity: tiny values are often split/parse failures in these PDFs
    tiny = 0
    for row in (parsed.get("budget_details") or []):
        amt = row.get("amount")
        if isinstance(amt, int) and 0 <= amt <= 10:
            tiny += 1
    if tiny:
        flags.append(f"tiny_amount_rows:{tiny}")

    for row in (parsed.get("budget_details") or []):
        item = str(row.get("item") or "")
        if "＞" in item or ">" in item:
            flags.append("marker_in_budget_details")
            break
    return flags


@dataclasses.dataclass
class PageRecord:
    source_page: int
    raw_text: str
    cleaned_text: str
    parsed: dict[str, Any]


def parse_pdf_to_records(pdf_path: str, pages: list[int]) -> dict[str, Any]:
    raise RuntimeError("Use parse_pdf_to_records_with_options")


def parse_pdf_to_records_with_options(
    pdf_path: str,
    pages: list[int],
    *,
    ocr: bool,
    ocr_lang: str,
    tessdata_dir: str | None,
    ocr_dpi: int,
) -> dict[str, Any]:
    def score_parse(
        *,
        header: dict[str, Any],
        name: str | None,
        department: str | None,
        budget: dict[str, Any] | None,
        budget_details: list[dict[str, Any]] | None,
    ) -> int:
        score = 0
        if header.get("category"):
            score += 2
        if name:
            score += 2
        if department:
            score += 1
        if (budget or {}).get("total") is not None:
            score += 2
        if budget_details:
            score += 1
        return score

    max_pages = max(pages) if pages else 0
    raw_pages = _extract_text(pdf_path, 1, max_pages, layout=True)

    records: list[dict[str, Any]] = []
    for p in pages:
        raw = raw_pages[p - 1] if 1 <= p <= len(raw_pages) else ""
        cleaned = _clean_text_keep_structure(raw)
        used_ocr = False

        if ocr and (not cleaned or len(re.sub(r"\s+", "", cleaned)) < 30):
            # Heuristic: if pdftotext yields empty/very short text, OCR this page.
            ocr_text = _ocr_page(
                pdf_path,
                p,
                lang=ocr_lang,
                tessdata_dir=tessdata_dir,
                dpi=ocr_dpi,
            )
            cleaned_ocr = _clean_text_keep_structure(ocr_text)
            if cleaned_ocr and len(cleaned_ocr) > len(cleaned):
                cleaned = cleaned_ocr
                used_ocr = True

        if not cleaned:
            records.append(
                {
                    "source_page": p,
                    "type": "empty",
                    "text": "",
                    "extraction": {"used_ocr": used_ocr},
                }
            )
            continue

        header = _parse_header(cleaned)
        name, department = _parse_name_department(cleaned)
        name = _clean_project_name(name)
        purpose = _parse_purpose(cleaned)
        description = _parse_description(cleaned)
        budget = _parse_budget_heuristic(cleaned)
        budget_details = _parse_budget_details(cleaned)

        # Quality-driven OCR rescue: some pages have embedded text but garble the budget table/markers.
        # OCR only when the parse looks incomplete to avoid running it on every page.
        if ocr and not used_ocr:
            try:
                needs_rescue = False
                if not name or not department:
                    needs_rescue = True
                if (budget or {}).get("total") is None and "事業費" in cleaned:
                    needs_rescue = True
                if not budget_details and ("く予算内" in cleaned or "予算内訳" in cleaned):
                    needs_rescue = True

                if needs_rescue:
                    ocr_text = _ocr_page(
                        pdf_path,
                        p,
                        lang=ocr_lang,
                        tessdata_dir=tessdata_dir,
                        dpi=ocr_dpi,
                    )
                    cleaned_ocr = _clean_text_keep_structure(ocr_text)
                    if cleaned_ocr and cleaned_ocr != cleaned:
                        header2 = _parse_header(cleaned_ocr)
                        name2, department2 = _parse_name_department(cleaned_ocr)
                        name2 = _clean_project_name(name2)
                        budget2 = _parse_budget_heuristic(cleaned_ocr)
                        budget_details2 = _parse_budget_details(cleaned_ocr)

                        score1 = score_parse(
                            header=header, name=name, department=department, budget=budget, budget_details=budget_details
                        )
                        score2 = score_parse(
                            header=header2,
                            name=name2,
                            department=department2,
                            budget=budget2,
                            budget_details=budget_details2,
                        )
                        if score2 > score1:
                            cleaned = cleaned_ocr
                            used_ocr = True
                            header = header2
                            name = name2
                            department = department2
                            budget = budget2
                            budget_details = budget_details2
                            purpose = _parse_purpose(cleaned_ocr)
                            description = _parse_description(cleaned_ocr)
            except Exception:
                pass

        # Post-process budget totals from details when missing / and fill a single missing amount if possible.
        # Preserve raw values (before inference/fallback) so we can audit later.
        if isinstance(budget, dict):
            if "total_raw" not in budget:
                budget["total_raw"] = budget.get("total")
            rev = budget.get("revenue") if isinstance(budget.get("revenue"), dict) else {}
            if "general_raw" not in budget:
                budget["general_raw"] = rev.get("general")

        try:
            total = budget.get("total") if isinstance(budget, dict) else None
            if isinstance(budget_details, list) and budget_details:
                known_sum = sum(r.get("amount", 0) for r in budget_details if isinstance(r.get("amount"), int))
                missing_rows = [r for r in budget_details if r.get("amount") is None]
                if total is None and known_sum > 0:
                    budget["total"] = known_sum
                    budget["inferred_from_details"] = True
                    total = known_sum
                if total is not None and len(missing_rows) == 1 and known_sum < total:
                    missing_rows[0]["amount"] = int(total - known_sum)
                    missing_rows[0]["auto_filled"] = True
        except Exception:
            pass

        # Final fallback for display (and overwrite budget.total to the best estimate).
        # Priority: details_sum (S) when reliable > general (G) > table total (T).
        if isinstance(budget, dict):
            details_sum = 0
            details_missing = 0
            details_auto_filled = 0
            if isinstance(budget_details, list) and budget_details:
                for row in budget_details:
                    if row.get("auto_filled"):
                        details_auto_filled += 1
                    amt = row.get("amount")
                    if amt is None:
                        details_missing += 1
                        continue
                    if isinstance(amt, int):
                        details_sum += amt

            budget["details_sum"] = details_sum
            budget["details_missing_amounts"] = details_missing
            if details_auto_filled:
                budget["details_auto_filled_rows"] = details_auto_filled

            raw_total = budget.get("total_raw")
            raw_general = budget.get("general_raw")

            details_reliable = details_sum >= 100 and (details_missing == 0 or details_auto_filled > 0)
            threshold = None
            if details_sum > 0:
                threshold = max(50, int(details_sum * 0.05))
                budget["details_mismatch_threshold"] = threshold

            mismatch_total = False
            mismatch_general = False
            if details_reliable and isinstance(threshold, int):
                if isinstance(raw_total, int) and abs(raw_total - details_sum) > threshold:
                    mismatch_total = True
                if isinstance(raw_general, int) and abs(raw_general - details_sum) > threshold:
                    mismatch_general = True

            budget["mismatch_total_vs_details"] = mismatch_total
            budget["mismatch_general_vs_details"] = mismatch_general

            total_display: int | None = None
            total_source: str | None = None
            if details_reliable and details_sum > 0 and (raw_total is None or mismatch_total):
                total_display = int(details_sum)
                total_source = "details_sum"
            elif isinstance(raw_general, int):
                total_display = int(raw_general)
                total_source = "general"
            elif isinstance(raw_total, int):
                total_display = int(raw_total)
                total_source = "table_total"
            elif details_sum > 0:
                total_display = int(details_sum)
                total_source = "details_sum_weak"
            else:
                total_display = budget.get("total") if isinstance(budget.get("total"), int) else None
                total_source = "unknown"

            budget["total_display"] = total_display
            budget["total_display_source"] = total_source
            if total_display is not None:
                budget["total"] = total_display

        parsed: dict[str, Any] = {}
        parsed.update(header)
        if name:
            parsed["name"] = name
        if department:
            parsed["department"] = department
        if purpose:
            parsed["purpose"] = purpose
        if description:
            parsed["description"] = description
        if budget:
            parsed["budget"] = budget
        if budget_details:
            parsed["budget_details"] = budget_details

        nospace = re.sub(r"\s+", "", cleaned)
        if "category" in parsed and "name" in parsed:
            page_type = "project"
        elif re.search(r"令和\s*\d+年度", cleaned) and "一般会計" in nospace:
            page_type = "cover"
        elif len(nospace) <= 40 and ("費" in nospace or "政務活動費" in nospace):
            page_type = "heading"
        else:
            page_type = "unknown"
        records.append(
            {
                "source_page": p,
                "type": page_type,
                "parsed": parsed,
                # Keep for audit/debug (can be removed later)
                "text": cleaned,
                "extraction": {"used_ocr": used_ocr},
            }
        )
        # Attach quality flags at the top level for UI/QA convenience
        records[-1]["quality_flags"] = _quality_flags(records[-1])

    meta: dict[str, Any] = {
        "source_pdf": pdf_path,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pages_requested": pages,
        "page_count": _pdf_page_count(pdf_path),
        "extractor": {"tool": "pdftotext", "layout": True},
    }
    if ocr:
        meta["ocr"] = {"enabled": True, "lang": ocr_lang, "tessdata_dir": tessdata_dir, "dpi": ocr_dpi}
    return {"metadata": meta, "pages": records}


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Japanese budget PDFs into JSON (heuristic, pdftotext-based).")
    parser.add_argument("pdf", help="Path to PDF")
    parser.add_argument("--pages", default="all", help="Pages to parse: e.g. 1-5 or 1,3,5 or all")
    parser.add_argument("--out", default="-", help="Output JSON path ('-' for stdout)")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR fallback (tesseract) for empty/short pages")
    parser.add_argument("--ocr-lang", default="jpn+jpn_vert", help="Tesseract language(s), e.g. jpn or jpn+jpn_vert")
    parser.add_argument(
        "--tessdata-dir",
        default=None,
        help="Path to tessdata dir (e.g. NIHO/gov/tessdata). If omitted, system default is used.",
    )
    parser.add_argument("--ocr-dpi", type=int, default=300, help="DPI for rendering PDF pages before OCR")
    args = parser.parse_args()

    page_count = _pdf_page_count(args.pdf)
    pages = _parse_pages_arg(args.pages, page_count)
    doc = parse_pdf_to_records_with_options(
        args.pdf,
        pages,
        ocr=args.ocr,
        ocr_lang=args.ocr_lang,
        tessdata_dir=args.tessdata_dir,
        ocr_dpi=args.ocr_dpi,
    )

    out = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.out == "-":
        print(out)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)


if __name__ == "__main__":
    main()
