# NIHO 鎌倉市予算PDF→JSON 可視化プロジェクト history

このファイルは、鎌倉市の予算PDFを **市民が理解しやすい形（JSON＋ブラウザ表示）** に変換していくための、作業履歴・設計判断・現状課題・次の候補をまとめる進捗管理用ドキュメント。

（今後はこの `history.md` に、日付ごとの更新内容や判断を追記していく想定）

---

## 1. 目的（Why）

### 1-1. 最終目的
- NIHO（街のリビング）をオンラインメディアとして運営する上で、鎌倉市民が **財政の全体像** と **事業費の詳細** を見て理解できる状態を作る
- PDFしかない（検索できない・再利用できない）予算情報を、Web表示しやすい構造化データへ変換し、将来的にRAG/検索/比較に使えるようにする

### 1-2. 直近の成果物
- **事業費別詳細（事業ページ単位）**  
  `gikaihi.pdf`（議会費）等の予算書PDF → 事業単位 JSON（`*.all.json`）
- **財政全体像（俯瞰）**  
  `naiyo-setsumei.pdf`（総括表/性質別） → 俯瞰 JSON（`naiyo-setsumei.json`）＋インフォグラフィック表示

---

## 2. 全体アーキテクチャ（What）

このプロジェクトは「入力PDF」→「抽出・正規化」→「JSON化」→「ブラウザ可視化」というパイプラインで構成する。

### 2-1. 方式A: `pdftotext -layout` を主とする（ローカル）
- 目的: **最速で広範囲**に抽出し、Web表示やランキング/検索の基盤を作る
- 強み:
  - 埋め込みテキストがあるPDFでは精度が高い
  - ネット不要・低コスト・高速
- 弱み:
  - 表（列）や縦積み数字の崩れに弱い
  - “見た目の構造” を復元するためのヒューリスティックが必要

### 2-2. 方式B: OCR（Tesseract / Cloud Vision）を併用（ハイブリッド）
- 目的: `pdftotext` が崩れる/欠損するページを **ピンポイント**に補完する
- 強み:
  - 画像ベース/埋め込みテキストが壊れているPDFに強い
  - bbox（座標）を使えば表復元の可能性が上がる
- 弱み:
  - 誤読が起きうる（特に日本語や数字）
  - コスト/インフラが増える（Cloud Visionの場合）

---

## 3. 主要コンポーネント（Where）

### 3-1. 事業費別詳細（pdftotext方式）
- パーサ: `NIHO/gov/parse_budget_pdf.py`
- 入力例:
  - `NIHO/gov/gikaihi.pdf`（議会費・110ページ）
  - `NIHO/gov/rodohi.pdf`（労働費）
  - `NIHO/gov/shobohi.pdf`（消防費）
  - `NIHO/gov/minseihi.pdf`（民生費）など
- 出力例:
  - `NIHO/gov/gikaihi.all.json`
  - `NIHO/gov/rodohi.all.json`
  - `NIHO/gov/shobohi.all.json`
  - `NIHO/gov/minseihi.all.json`

補足:
- `pdftotext` 抽出の崩れに対して、以下を追加してきた
  - 事業名/担当課のノイズ除去（装飾記号、先頭の数字・ローマ数字、`】` 等）
  - 予算内訳の “節 + 項目 + 金額” 抽出の安定化（`>` 混入などの除去）
  - **事業費（合計）の誤抽出に対するフォールバック**（内訳合計/一般財源等）
  - QA用の `quality_flags`（要確認ページの抽出）

関連ドキュメント:
- `NIHO/gov/review-all.md`（gikaihi.all.json の誤り傾向、原因、改善の方向性）

### 3-2. 財政全体像（概要テーブル）
- パーサ: `NIHO/gov/parse_overview_pdf.py`
- 入力:
  - `NIHO/gov/naiyo-setsumei.pdf`
    - p.7: 一般会計予算総括表（歳出）…款別/前年差
    - p.8: 一般会計歳出予算性質別内訳表…款×性質別
- 出力:
  - `NIHO/gov/naiyo-setsumei.json`

実装上の重要ポイント:
- p.8（性質別）は数字が縦に分割されやすく、列が密集しているため
  - x近傍で拾う方式だと「隣列の数字が混ざって連結される」事故が起きやすい
  - そのため **`pdftotext -layout` の文字カラムをスライスして列ごとに抽出**する方式を採用
- p.7（款別）は行検出が崩れやすい（例: `商工費` が `商` と `工費` に割れる）ため
  - **複数行（2行連結）でも行開始を検出**する方式を採用
- 検証:
  - p.7の款別金額合計と、p.8の性質別「計」が **全件一致することをチェック**している

### 3-3. ブラウザ表示（静的HTML）
- 事業費別詳細ビューア: `NIHO/gov/viewer/index.html`
  - JSONファイルをローカルで読み込み（ファイル入力）
  - 検索、並び替え、事業ページの展開表示など
- 財政全体像ビューア: `NIHO/gov/viewer/overview.html`
  - 円グラフ（款別構成比）
  - 棒グラフ（款別前年差）
  - 性質別内訳（選択した款の比率表示）

### 3-4. 変換・運用補助
- CSVエクスポート: `NIHO/gov/export_projects_csv.py`
  - `*.all.json`（type=project）をCSVへ出力
  - スプレッドシート/Notion/外部分析向け
- ローカルサーバ（任意）: `NIHO/gov/serve_viewer.py`
  - `file://` 制約がある場合にHTTPで配信するための簡易サーバ

### 3-5. OCR（Cloud Vision）プロトタイプ
（pdftotext方式で取りづらいケースの補完候補）
- v1: `NIHO/gov/kamakura-budget-ocr-v1/`（GCVを使うOCRパイプラインの雛形）
- v2: `NIHO/gov/kamakura-budget-ocr-v2/`（改良版のパイプライン）

注意:
- Cloud Visionを使う場合はGCPの設定が必要（後述）
- **認証情報（service account key）はリポジトリにコミットしない**（ローカル運用・gitignore推奨）

---

## 4. 実行手順（How）

### 4-1. 前提（ローカル）
- Python 3 系
- `pdftotext` / `pdfinfo`（Poppler）
- （OCR併用時）`tesseract` と `NIHO/gov/tessdata/` の学習データ

### 4-2. 事業費別詳細 JSON 生成（pdftotext中心）
例:
```bash
python3 NIHO/gov/parse_budget_pdf.py NIHO/gov/gikaihi.pdf --pages all --out NIHO/gov/gikaihi.all.json
```

（OCRフォールバックを有効にする例）
```bash
python3 NIHO/gov/parse_budget_pdf.py NIHO/gov/gikaihi.pdf \
  --pages all \
  --ocr \
  --tessdata-dir NIHO/gov/tessdata \
  --out NIHO/gov/gikaihi.all.json
```

### 4-3. 財政全体像 JSON 生成（naiyo-setsumei）
```bash
python3 NIHO/gov/parse_overview_pdf.py NIHO/gov/naiyo-setsumei.pdf --out NIHO/gov/naiyo-setsumei.json
```

### 4-4. ブラウザで見る
- 直接開く（推奨: ファイル入力でJSONを選択）
  - `NIHO/gov/viewer/index.html`
  - `NIHO/gov/viewer/overview.html`

- HTTPで開く（任意）
```bash
python3 NIHO/gov/serve_viewer.py --port 8000
```

---

## 5. インフラ構成（Infrastructure）

### 5-1. 現状（ローカル中心）
- 変換: ローカルPythonスクリプト（`pdftotext` 呼び出し）
- 可視化: 静的HTML（JSのみ、外部CDN依存なし）
- 配信（任意）: Pythonの簡易HTTPサーバ

### 5-2. 将来候補（Cloud Vision / GCP）
Cloud Vision（非同期PDF OCR）を回す場合の典型構成:
- GCPプロジェクト
  - Cloud Vision API 有効化
  - Service Account 作成（キーJSON）
- GCSバケット
  - input: PDF置き場
  - output: OCR結果JSON置き場
- 実行環境
  - `GOOGLE_APPLICATION_CREDENTIALS=/path/to/credential.json`
  - `gsutil` or GCS SDK

セキュリティ注意:
- `NIHO/gov/fabled-opus-482418-m6-aea2e68d1cc3.json` のような認証情報ファイルは、
  **公開リポジトリに絶対に含めない**（gitignore・権限・共有範囲の管理）

---

## 6. 現状の課題（Issues / Risks）

### 6-1. PDF構造の多様性
- 款によってテンプレが違う、同じ款でもページにより表の崩れ方が違う
- `pdftotext` の出力は安定しないことがある（装飾罫線、縦積み数字、フォント）

### 6-2. 「事業費（合計）」の信頼性
- `budget_details` は比較的高精度で取れる一方、事業費テーブル（総額/財源内訳）は崩れやすい
- 対策として `budget.total_display` のように **UI表示用の推定値**を採用し、由来を保持する設計にしている

### 6-3. QA/レビュー負荷
- 自動抽出は100%にならないため、**要確認フラグ**とレビュー導線が必須
- “どのページが怪しいか” を機械的に見つける（mismatch、欠損、ノイズ混入）ことが重要

### 6-4. 表示（UI）の改善余地
- 現状のビューアは試作。検索/絞り込み/比較/注釈表示などのUX改善余地が大きい

---

## 7. 今後の作業候補（Next）

### 7-1. データ面（精度・拡張）
- `parse_budget_pdf.py` の `budget.revenue`（財源内訳）精度改善（列推定の強化）
- `quality_flags` の強化（例: 事業名ノイズ、担当課欠損、内訳合計不整合）
- 款横断で共通化できる正規化（課名辞書、ノイズ文字の更新）
- “怪しいページだけ” OCR/座標抽出に回すハイブリッド運用の確立

### 7-2. 可視化（UI）
- “財政全体像” と “事業費別詳細” を統合する導線（タブ/リンク/パンくず）
- 款別→事業一覧へのジャンプ（overview → detail）
- 前年比較の表現強化（増減率トグル、前年差のランキングなど）
- 公開用のUI（注釈、定義、単位、免責、データ更新日）

### 7-3. 運用・公開
- JSON生成をワンコマンド化（Makefileや簡易スクリプト）
- データ更新（年度更新）時の差分管理（ファイル命名規則、バージョニング）
- 公開時のホスティング（GitHub Pages / Vercel / S3 等）を検討

---

## 8. メモ（運用ルール案）

- “厳密な決算値” ではなく “予算段階の理解” が目的なので、UIでは `budget.total_display` を正として扱う
- ただし、後から監査/検証できるように
  - 生値（raw）
  - 推定値（display）
  - 推定根拠（source/flags）
  を JSON 内に残す

---

## 9. 更新ログ（追記欄）

今後ここに日付ごとに追記する。

- YYYY-MM-DD: （例）`gikaihi.pdf` 再生成、`budget.total_display` のルール追加、overviewビューア改善…など
- 2025-12-27: `nihogov` リポジトリを作成し、`NIHO/gov` を独立リポジトリとして初期コミット→GitHubへpush（巨大な `.venv/`・OCR出力・PDF・生成JSON・credential は `.gitignore` で除外、README競合はrebaseで解消）


<!-- HISTORY:AUTO:START -->
## 自動追記（git log）

- 対象パス: `.`
- 生成時刻: `2025-12-27T07:50:14.397150+00:00`
- 反映コミット数: 3

### 直近の変更（新しい順）

#### 2025-12-27
- `3813d59` Update viewers
  - `viewer/index.html`
  - `viewer/overview.html`
- `54ec4e7` Initial commit: budget PDF parsers + viewers
  - `.gitignore`
  - `README.md`
  - `export_projects_csv.py`
  - `history.md`
  - `kamakura-budget-ocr-v1/README.md`
  - `kamakura-budget-ocr-v1/config.py`
  - `kamakura-budget-ocr-v1/example/run_sample.sh`
  - `kamakura-budget-ocr-v1/gcv_client.py`
  - `kamakura-budget-ocr-v1/helpers.py`
  - `kamakura-budget-ocr-v1/json_converter.py`
  - `kamakura-budget-ocr-v1/layout_reconstructor.py`
  - `kamakura-budget-ocr-v1/ocr_normalizer.py`
  - `kamakura-budget-ocr-v1/ocr_pipeline.py`
  - `kamakura-budget-ocr-v1/project_segmenter.py`
  - `kamakura-budget-ocr-v1/requirements.txt`
  - `kamakura-budget-ocr-v1/review_ui.py`
  - `kamakura-budget-ocr-v1/validator.py`
  - `kamakura-budget-ocr-v2/README.md`
  - `kamakura-budget-ocr-v2/config.py`
  - `kamakura-budget-ocr-v2/docai_fallback.py`
  - `kamakura-budget-ocr-v2/gcs_vision_client.py`
  - `kamakura-budget-ocr-v2/json_converter_v2.py`
  - `kamakura-budget-ocr-v2/layout_reconstructor_v2.py`
  - `kamakura-budget-ocr-v2/pipeline.py`
  - `kamakura-budget-ocr-v2/requirements.txt`
  - `kamakura-budget-ocr-v2/review.md`
  - `parse_budget_pdf.py`
  - `parse_overview_pdf.py`
  - `project.md`
  - `review-all.md`
  - `serve_viewer.py`
  - `tessdata/jpn.traineddata`
  - `tessdata/jpn_vert.traineddata`
  - `update_history_from_git.py`
  - `viewer/index.html`
  - `viewer/overview.html`
- `a5d1c72` Initial commit
  - `README.md`

<!-- HISTORY:AUTO:END -->
