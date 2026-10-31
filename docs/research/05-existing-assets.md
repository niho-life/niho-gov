# 調査メモ 05: 既存の試作（2025-12 の 2 プロジェクト）

作成 2026-10-31。どちらも hihirohub（外付け SSD）`/Volumes/hihirohub/download-hi/` にある。

## gov（= GitHub takuyatakahamaT/nihogov、private、最終 push 2025-12-27）

鎌倉市の予算 PDF を構造化 JSON にして、ブラウザで見る試作。

- 方式 A `parse_budget_pdf.py`: `pdftotext -layout` のヒューリスティック抽出。事業ページ単位の JSON（事業名・担当課・目的・説明・事業費・節ごとの内訳・財源・quality_flags）。議会費（110 ページ）・労働費・消防費・民生費を変換済み。
- 方式 B `kamakura-budget-ocr-v1/v2`: Cloud Vision の非同期 OCR → KMeans で列推定 → JSON → 検証 → Document AI フォールバック。GCP 設定が要る。
- `parse_overview_pdf.py`: 総括表（款別・前年差）と性質別内訳 → `naiyo-setsumei.json`。款別合計と性質別「計」の全件一致を検証済み。
- `parse_revenue_pdf.py`: 歳入 → `sainyu-setsumei.json`。
- `viewer/index.html`（事業費別詳細: 検索・並び替え・展開）、`viewer/overview.html`（円グラフ・前年差の棒・性質別の積み上げ）。
- `serve_viewer.py` + `chatbot.py`: `/api/chat` で Claude/Gemini に JSON を渡して答える試作（鍵は .env）。
- `history.md`: 設計判断と課題。課題は「PDF 構造の多様性」「事業費（合計）の信頼性」「QA 負荷」「UI の改善余地」。次の候補は「全款の変換」「経年比較」「事業の結果ページへのリンク」「RAG」。
- `review-all.md`: 誤抽出の傾向。

含意: 款別・性質別・歳入の俯瞰は **そのまま使える**。事業ページ単位は 4 款分で、全款（14 款）に広げる作業と、`「会 計 年 度 任 用 …」` のような空白混入の正規化が要る。

## gikai（git 管理なし）

2025 年 6 月・9 月定例会の本会議録をテーマ別に読む試作。

- 会議録: `0903.md`〜`0930.md`（9 月定例会・日ごと）、`gikai_6.md`（6 月）、`gikai_9.md`（9 月の統合・2MB）。
- `gikai_theme_view.py`: キーワード一致でテーマ付け → `out/themes.json`・`out/themes/<theme>.json`、`out/gikai_9_blocks.json`（発言ブロック）。
- `theme_keywords.json`: 7 テーマ（新庁舎・防災・教育・下水道・観光・子育て・福祉）と説明。`theme_explanations.json`（簡単解説）。
- `view/`: サイドバーにテーマ、本文に「簡単解説」→ 発言ブロック（原文）。キーワード検索。
- `article-highlight.md`: NIHO 文体のハイライト記事見本（「市役所が 2 つになる！？」9 月議会の 5 トピック）。`article-sample-kato.md`: 議員 1 人の質疑の記事見本。
- `styleguide.md`: NIHO kamakura のデザインルール（クリーム背景・緑のアクセント・余白多め）。
- `project.md`: 目的は「議事録が長すぎて読めず、個別の質問単位でしか把握できない → 町の Wiki のようにテーマごとに経緯を抽出」。todo に委員会の会議録・チャット bot・ホスティング。

含意: 「テーマ → 簡単解説 → 原文」の 3 層と、NIHO 文体の記事化は **構想の中核としてそのまま活きる**。キーワード一致のテーマ付けは誤分類が出るので、LLM によるテーマ付け・経緯の要約に置き換える。
