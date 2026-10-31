#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any


def _run(args: list[str]) -> str:
    return subprocess.check_output(args, stderr=subprocess.STDOUT).decode("utf-8", "replace")


def _pdftotext_pages(pdf_path: str, *, first: int, last: int) -> list[str]:
    raw = _run(["pdftotext", "-layout", "-f", str(first), "-l", str(last), pdf_path, "-"])
    pages = raw.split("\f")
    expected = last - first + 1
    if len(pages) >= expected:
        pages = pages[:expected]
    else:
        pages += [""] * (expected - len(pages))
    return pages


def _collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parse_reiwa_year(text: str) -> int | None:
    m = re.search(r"令\s*和\s*(\d+)\s*年\s*度", text)
    if not m:
        return None
    return int(m.group(1))


@dataclass
class _Cluster:
    center: float
    xs: list[int]


def _cluster_x_positions(xs: list[int], *, tol: int = 4) -> list[_Cluster]:
    clusters: list[_Cluster] = []
    for x in sorted(xs):
        placed = False
        for c in clusters:
            if abs(x - c.center) <= tol:
                c.xs.append(x)
                c.center = sum(c.xs) / len(c.xs)
                placed = True
                break
        if not placed:
            clusters.append(_Cluster(center=float(x), xs=[x]))
    return clusters


def _extract_table_lines(page_text: str, *, start_pat: str, end_pat: str | None) -> list[str]:
    lines = [ln.rstrip("\n") for ln in page_text.splitlines()]
    start = 0
    for i, ln in enumerate(lines):
        if re.search(start_pat, ln):
            start = i
            break
    end = len(lines)
    if end_pat:
        for j in range(start, len(lines)):
            if re.search(end_pat, lines[j]):
                end = j
                break
    return lines[start:end]


def _extract_number_by_x(
    lines: list[str],
    *,
    y0: int,
    y1: int,
    x_center: float,
    x_tol: int = 7,
) -> int | None:
    """
    Extract a number rendered as vertically split digit fragments near a fixed x position.
    Example fragments: "1" + "0,1" + "34,3" + "05" => "10,134,305" => 10134305
    """
    frag_re = re.compile(r"[△\-–—]?\d[\d,]*")
    # Match comma-leading fragments that are split onto their own token, e.g. ",800".
    # Avoid double-capturing inside a normal comma-number like "440,051".
    comma_frag_re = re.compile(r"(?<!\d),\d{1,3}")
    fragments: list[tuple[int, int, str]] = []
    for y in range(y0, min(y1, len(lines))):
        ln = lines[y]
        for m in frag_re.finditer(ln):
            x = m.start()
            if x < 20:
                continue
            if abs(x - x_center) > x_tol:
                continue
            tok = m.group(0)
            fragments.append((y, x, tok))
        # Also capture comma-leading fragments like ",800" which commonly occur on the next line.
        for m in comma_frag_re.finditer(ln):
            x = m.start()
            if x < 20:
                continue
            if abs(x - x_center) > x_tol:
                continue
            fragments.append((y, x, m.group(0)))
    if not fragments:
        return None
    fragments.sort(key=lambda t: (t[0], t[1]))
    joined = "".join(tok for _, _, tok in fragments)
    joined = joined.replace("△", "-")
    joined = re.sub(r"[^0-9\\-]", "", joined)
    if not joined:
        return None
    try:
        return int(joined)
    except Exception:
        return None


def _extract_number_by_slice(
    lines: list[str],
    *,
    y0: int,
    y1: int,
    x_left: int,
    x_right: int | None,
) -> int | None:
    """
    Extract a number from a fixed character-column slice produced by `pdftotext -layout`.

    This is more robust than x-center proximity when digits are densely packed across columns,
    because it avoids pulling fragments from adjacent columns.
    """
    parts: list[str] = []
    for y in range(max(0, y0), min(y1, len(lines))):
        ln = lines[y]
        seg = ln[x_left:x_right] if x_right is not None else ln[x_left:]
        if not seg.strip():
            continue
        seg = seg.replace("△", "-")
        # Drop decimal tokens like "0.6" (構成比/伸び率) which should never be part of amount columns.
        seg = re.sub(r"\d+\.\d+", " ", seg)
        cleaned = re.sub(r"[^0-9,\\-]", "", seg)
        if cleaned:
            parts.append(cleaned)
    if not parts:
        return None
    joined = "".join(parts)
    joined = joined.replace(",", "")
    joined = re.sub(r"[^0-9\\-]", "", joined)
    if not joined:
        return None
    # Normalize stray '-' occurrences (keep only a single leading '-').
    if "-" in joined[1:]:
        joined = ("-" if joined.startswith("-") else "") + joined.replace("-", "")
    try:
        return int(joined)
    except Exception:
        return None


def _centers_to_slices(centers: list[float], *, min_left: int = 20) -> list[tuple[int, int | None]]:
    """
    Convert detected x-centers into non-overlapping [left, right) slices.
    Boundaries are midpoints between adjacent centers.
    """
    if not centers:
        return []
    mids: list[int] = []
    for i in range(len(centers) - 1):
        mids.append(int((centers[i] + centers[i + 1]) / 2))
    slices: list[tuple[int, int | None]] = []
    for i in range(len(centers)):
        left = mids[i - 1] + 1 if i > 0 else min_left
        right = mids[i] if i < len(mids) else None
        left = max(min_left, left)
        if right is not None and right <= left:
            right = left + 1
        slices.append((left, right))
    return slices


def _find_line_index(lines: list[str], patterns: list[str], *, start: int = 0) -> int | None:
    for i in range(start, len(lines)):
        ln = lines[i]
        for pat in patterns:
            if re.search(pat, ln):
                return i
    return None


KAMOKU_ORDER: list[dict[str, Any]] = [
    {"code": 5, "name": "議会費", "patterns": [r"議.*費"]},
    {"code": 10, "name": "総務費", "patterns": [r"総.*務.*費", r"務.*費"]},
    {"code": 15, "name": "民生費", "patterns": [r"民.*生.*費"]},
    {"code": 20, "name": "衛生費", "patterns": [r"衛.*生.*費"]},
    {"code": 25, "name": "労働費", "patterns": [r"労.*働.*費", r"働.*費", r"たヵ"]},
    {"code": 30, "name": "農林水産業費", "patterns": [r"(農|苧).*林.*水.*産.*業.*費", r"水.*産.*業.*費"]},
    {"code": 35, "name": "商工費", "patterns": [r"商.*工.*費"]},
    {"code": 40, "name": "観光費", "patterns": [r"観.*光.*費"]},
    {"code": 45, "name": "土木費", "patterns": [r"土.*木"]},
    {"code": 50, "name": "消防費", "patterns": [r"消.*防.*費"]},
    {"code": 55, "name": "教育費", "patterns": [r"教.*費", r"教.*円.*費", r"目.*費"]},
    {"code": 60, "name": "公債費", "patterns": [r"公.*債.*費"]},
    {"code": 65, "name": "諸支出金", "patterns": [r"諸.*支.*出.*金"]},
    {"code": 70, "name": "予備費", "patterns": [r"予.*備.*費"]},
]


def parse_expenditure_by_kamoku(page7_text: str) -> dict[str, Any]:
    lines = _extract_table_lines(page7_text, start_pat=r"歳出", end_pat=r"※構成比")
    # Determine amount column centers by clustering numeric tokens (digits+commas) across the table.
    comma_num = re.compile(r"\d{1,3}(?:,\d{3})+")
    xs: list[int] = []
    for ln in lines:
        for m in comma_num.finditer(ln):
            if m.start() >= 20:
                xs.append(m.start())
    clusters = _cluster_x_positions(xs, tol=4)
    clusters = sorted(clusters, key=lambda c: len(c.xs), reverse=True)
    # Two most frequent numeric columns correspond to 令和7金額 / 令和6金額 in this PDF layout.
    amount_centers = sorted([c.center for c in clusters[:2]])
    if len(amount_centers) != 2:
        raise RuntimeError("Failed to detect amount columns on page 7")
    cur_center, prev_center = amount_centers[0], amount_centers[1]

    def find_row_start_multiline(patterns: list[str], *, start: int) -> int | None:
        for i in range(start, len(lines)):
            a = lines[i]
            b = lines[i + 1] if i + 1 < len(lines) else ""
            ab = f"{a} {b}"
            for pat in patterns:
                if re.search(pat, a) or re.search(pat, ab):
                    return i
        return None

    # Find row boundaries (y ranges) using multiline pattern matches.
    # Page7 often splits "商工費" like:
    #   "5 商"
    #   "3 工 費 ...."
    starts: list[int] = []
    cursor = 0
    for item in KAMOKU_ORDER:
        y = find_row_start_multiline(item["patterns"], start=cursor)
        if y is None:
            raise RuntimeError(f"Failed to locate row start for code={item['code']} ({item['name']}) on page 7")
        starts.append(y)
        cursor = y + 1
    # Find total line
    total_y = _find_line_index(lines, [r"歳.*出.*合.*計"], start=0) or len(lines) - 1

    # Ensure starts are non-decreasing and within range
    fixed_starts: list[int] = []
    last = 0
    for y in starts:
        y2 = max(last, min(y, total_y))
        fixed_starts.append(y2)
        last = y2

    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(KAMOKU_ORDER):
        y0 = fixed_starts[idx]
        y1 = fixed_starts[idx + 1] if idx + 1 < len(fixed_starts) else total_y
        cur = _extract_number_by_x(lines, y0=y0, y1=y1, x_center=cur_center, x_tol=6)
        prev = _extract_number_by_x(lines, y0=y0, y1=y1, x_center=prev_center, x_tol=6)
        rows.append(
            {
                "code": item["code"],
                "name": item["name"],
                "current": cur,
                "previous": prev,
                "y_range": [y0, y1],
            }
        )

    total_current = _extract_number_by_x(lines, y0=total_y, y1=len(lines), x_center=cur_center, x_tol=6)
    total_previous = _extract_number_by_x(lines, y0=total_y, y1=len(lines), x_center=prev_center, x_tol=6)

    # Compute derived fields
    for r in rows:
        cur = r.get("current")
        prev = r.get("previous")
        if isinstance(cur, int) and isinstance(prev, int):
            r["diff"] = cur - prev
            r["rate"] = (cur - prev) / prev * 100 if prev != 0 else None
        else:
            r["diff"] = None
            r["rate"] = None
        if isinstance(cur, int) and isinstance(total_current, int) and total_current:
            r["share"] = cur / total_current * 100
        else:
            r["share"] = None
        if isinstance(prev, int) and isinstance(total_previous, int) and total_previous:
            r["previous_share"] = prev / total_previous * 100
        else:
            r["previous_share"] = None

    return {
        "unit": "千円",
        "current_total": total_current,
        "previous_total": total_previous,
        "amount_column_centers": amount_centers,
        "items": rows,
    }


NATURE_COLUMNS: list[dict[str, str]] = [
    {"key": "personnel", "label": "人件費"},
    {"key": "goods_services", "label": "物件費"},
    {"key": "maintenance", "label": "維持補修費"},
    {"key": "assistance", "label": "扶助費"},
    {"key": "subsidies", "label": "補助費等"},
    {"key": "construction", "label": "建設事業費"},
    {"key": "debt_reserve", "label": "公債費・予備費"},
    {"key": "investment_loan", "label": "投資・出資・貸付金"},
    {"key": "reserve_fund", "label": "積立金"},
    {"key": "transfers", "label": "繰出金"},
    {"key": "total", "label": "計"},
]


def parse_nature_breakdown(page8_text: str) -> dict[str, Any]:
    lines = _extract_table_lines(page8_text, start_pat=r"一般会計歳出予算性質別内訳表", end_pat=r"※構成比")

    num_frag = re.compile(r"\d[\d,]*")
    xs: list[int] = []
    for ln in lines:
        for m in num_frag.finditer(ln):
            if m.start() >= 20:
                xs.append(m.start())
    clusters = _cluster_x_positions(xs, tol=4)
    clusters = sorted(clusters, key=lambda c: len(c.xs), reverse=True)
    # Choose the top N clusters as columns. The PDF layout is stable for this table.
    centers = sorted([c.center for c in clusters[: len(NATURE_COLUMNS)]])
    if len(centers) != len(NATURE_COLUMNS):
        raise RuntimeError("Failed to detect nature table columns on page 8")
    slices = _centers_to_slices(centers, min_left=20)

    def extract_row_values(y0: int, y1: int) -> dict[str, int]:
        values: dict[str, int] = {}
        for ci, col in enumerate(NATURE_COLUMNS):
            x_left, x_right = slices[ci]
            v = _extract_number_by_slice(lines, y0=y0, y1=y1, x_left=x_left, x_right=x_right)
            values[col["key"]] = int(v) if isinstance(v, int) else 0
        return values

    def find_row_start_by_keyword(keyword: str, *, start: int) -> int | None:
        for i in range(start, len(lines)):
            s = lines[i].lstrip()
            if not s:
                continue
            # Require a leading digit to avoid matching header labels like "公債費・..."
            if not s[0].isdigit():
                continue
            if keyword in lines[i]:
                return i
        return None

    # Row boundary detection (nature table has more garbling; use keyword anchors instead of strict patterns)
    keyword_by_code: dict[int, list[str]] = {
        5: ["議"],
        10: ["総"],
        15: ["民"],
        20: ["衛"],
        25: ["労", "働"],
        30: ["農", "水"],
        35: ["商", "工"],
        40: ["観", "光"],
        45: ["土", "木", "木"],
        50: ["消", "防"],
        55: ["教", "円"],
        60: ["公", "債"],
        65: ["諸"],
        70: ["予", "備"],
    }

    start_indices: list[int] = []
    cursor = 0
    for item in KAMOKU_ORDER:
        keywords = keyword_by_code.get(item["code"], [item["name"][0]])
        y = None
        for kw in keywords:
            y = find_row_start_by_keyword(kw, start=cursor)
            if y is not None:
                break
        if y is None:
            raise RuntimeError(f"Failed to locate row start for code={item['code']} ({item['name']}) on page 8")
        start_indices.append(y)
        cursor = y + 1

    total_y = _find_line_index(lines, [r"^\s*合\s*計"], start=0) or (len(lines) - 1)

    fixed: list[int] = []
    last = 0
    for y in start_indices:
        y2 = max(last, min(y, total_y))
        fixed.append(y2)
        last = y2

    items: list[dict[str, Any]] = []
    for idx, item in enumerate(KAMOKU_ORDER):
        y0 = fixed[idx]
        y1 = fixed[idx + 1] if idx + 1 < len(fixed) else total_y
        vals = extract_row_values(y0, y1)
        total = vals.get("total") or 0
        shares: dict[str, float] = {}
        if total > 0:
            for col in NATURE_COLUMNS:
                k = col["key"]
                if k == "total":
                    continue
                shares[k] = vals.get(k, 0) / total * 100
        items.append({"code": item["code"], "name": item["name"], "values": vals, "shares": shares, "y_range": [y0, y1]})

    # Stop totals extraction before the "構成比" row; otherwise percent values get concatenated.
    ratio_y = _find_line_index(lines, [r"構\s*成\s*比"], start=total_y) or len(lines)
    totals = extract_row_values(total_y, ratio_y)
    return {
        "unit": "千円",
        "columns": NATURE_COLUMNS,
        "column_centers": centers,
        "column_slices": slices,
        "totals": totals,
        "items": items,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse naiyo-setsumei.pdf (budget overview tables) into JSON.")
    ap.add_argument("pdf", help="Path to naiyo-setsumei.pdf")
    ap.add_argument("--out", default="-", help="Output JSON path ('-' for stdout)")
    args = ap.parse_args()

    pages = _pdftotext_pages(args.pdf, first=1, last=8)
    reiwa = _parse_reiwa_year(pages[0]) or _parse_reiwa_year("\n".join(pages))  # fallback scan

    page7 = pages[6]
    page8 = pages[7]

    by_kamoku = parse_expenditure_by_kamoku(page7)
    by_nature = parse_nature_breakdown(page8)

    doc = {
        "metadata": {
            "source_pdf": args.pdf,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "fiscal_year_reiwa": reiwa,
            "unit": "千円",
        },
        "expenditure_by_kamoku": by_kamoku,
        "expenditure_nature_by_kamoku": by_nature,
    }

    out = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.out == "-":
        print(out)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)


if __name__ == "__main__":
    main()
