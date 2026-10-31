#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


CSV_HEADER = [
    "source_key",
    "source_label",
    "source_pdf",
    "source_page",
    "category_kuan_code",
    "category_kuan_name",
    "category_kou_code",
    "category_kou_name",
    "category_moku_code",
    "category_moku_name",
    "field",
    "policy",
    "project_name",
    "department",
    "prev_year_page",
    "budget_unit",
    "budget_total_display",
    "budget_total_display_source",
    "budget_total_raw",
    "budget_general_raw",
    "budget_details_sum",
    "budget_details_missing_amounts",
    "quality_flags",
    "purpose_target",
    "purpose_intent",
    "purpose_effect",
    "description",
    "budget_details",
]


def _budget_details_to_text(budget_details: Any) -> str:
    if not isinstance(budget_details, list) or not budget_details:
        return ""
    parts: list[str] = []
    for row in budget_details:
        if not isinstance(row, dict):
            continue
        section = row.get("section") or ""
        item = row.get("item") or ""
        qty = f"（{row.get('quantity')}）" if row.get("quantity") else ""
        amount = row.get("amount")
        amount_s = "" if amount is None else str(amount)
        parts.append(f"{section}:{item}{qty}:{amount_s}")
    return " | ".join(parts)


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export type=project pages from budget JSON to CSV.")
    parser.add_argument("json_path", help="Path to JSON (e.g. NIHO/gov/kamakura-fin.json)")
    parser.add_argument("--out", required=True, help="Output CSV path")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    out_path = Path(args.out)

    doc = _read_json(json_path)
    pages = doc.get("pages") if isinstance(doc, dict) else None
    if not isinstance(pages, list):
        raise SystemExit("Invalid JSON: expected {pages:[...]}")

    rows: list[list[str]] = [CSV_HEADER]
    for page in pages:
        if not isinstance(page, dict):
            continue
        if page.get("type") != "project":
            continue

        parsed = page.get("parsed") if isinstance(page.get("parsed"), dict) else {}
        budget = parsed.get("budget") if isinstance(parsed.get("budget"), dict) else {}
        revenue = budget.get("revenue") if isinstance(budget.get("revenue"), dict) else {}
        category = parsed.get("category") if isinstance(parsed.get("category"), dict) else {}
        source = page.get("source") if isinstance(page.get("source"), dict) else {}
        purpose = parsed.get("purpose") if isinstance(parsed.get("purpose"), dict) else {}

        flags = page.get("quality_flags")
        flags_s = " | ".join(flags) if isinstance(flags, list) else ""
        desc = parsed.get("description")
        desc_s = " / ".join(desc) if isinstance(desc, list) else ""

        kuan = category.get("kuan") if isinstance(category.get("kuan"), dict) else {}
        kou = category.get("kou") if isinstance(category.get("kou"), dict) else {}
        moku = category.get("moku") if isinstance(category.get("moku"), dict) else {}

        rows.append(
            [
                _as_str(source.get("key")),
                _as_str(source.get("label")),
                _as_str(source.get("pdf")),
                _as_str(page.get("source_page")),
                _as_str(kuan.get("code")),
                _as_str(kuan.get("name")),
                _as_str(kou.get("code")),
                _as_str(kou.get("name")),
                _as_str(moku.get("code")),
                _as_str(moku.get("name")),
                _as_str(parsed.get("field")),
                _as_str(parsed.get("policy")),
                _as_str(parsed.get("name")),
                _as_str(parsed.get("department")),
                _as_str(parsed.get("prev_year_page")),
                _as_str(budget.get("unit")),
                _as_str(budget.get("total_display") if budget.get("total_display") is not None else budget.get("total")),
                _as_str(budget.get("total_display_source")),
                _as_str(budget.get("total_raw")),
                _as_str(revenue.get("general") if revenue.get("general") is not None else budget.get("general_raw")),
                _as_str(budget.get("details_sum")),
                _as_str(budget.get("details_missing_amounts")),
                flags_s,
                _as_str(purpose.get("target")),
                _as_str(purpose.get("intent")),
                _as_str(purpose.get("effect")),
                desc_s,
                _budget_details_to_text(parsed.get("budget_details")),
            ]
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerows(rows)

    print(f"Wrote {out_path} ({len(rows) - 1} projects)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

