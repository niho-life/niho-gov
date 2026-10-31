# tools/minutes — 会議録をテーマ別に読む試作（2025-12）

鎌倉市議会の会議録（会議録検索システムから取得した Markdown）を、キーワード一致でテーマごとの発言ブロックに分け、静的 HTML で読む試作です。構想（`docs/design/00-concept.md`）の F1「今回の議会」・F2「テーマの経緯」の原型。

- `merge_minutes.py`: 日ごとの会議録 Markdown を 1 つに結合する
- `gikai_theme_view.py`: `theme_keywords.json` のテーマごとに発言ブロックを抽出し `out/themes.json` を書く
- `view/`: テーマ一覧 → 簡単解説 → 原文、の静的ビューア（`python3 -m http.server` で開く）
- `theme_explanations.json` / `theme_summaries.json`: テーマの簡単解説と要約

会議録の本文（数 MB）と `out/` は置いていません。元データは会議録検索システム https://www.kensakusystem.jp/kamakura/index.html から。
