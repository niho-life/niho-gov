# nihogov

鎌倉市の予算PDFを **構造化JSON** に変換し、ブラウザで閲覧しやすくするための試作ツール群です。

- 事業費別詳細（事業ページ単位のJSON）: `parse_budget_pdf.py`
- 財政全体像（款別＋性質別の俯瞰JSON）: `parse_overview_pdf.py`
- ブラウザ表示（静的HTML）: `viewer/`

## 前提
- `pdftotext` / `pdfinfo`（Poppler）
- Python 3
- （OCR併用時）`tesseract`

## 使い方（事業費別詳細）

例: 議会費PDFを全ページJSON化

```bash
mkdir -p out
python3 parse_budget_pdf.py /path/to/gikaihi.pdf --pages all --out out/gikaihi.all.json
```

OCR（日本語）フォールバックを有効にする例（「pdftotextで空/極端に短いページ」だけOCR）:

```bash
mkdir -p out
python3 parse_budget_pdf.py /path/to/gikaihi.pdf \
  --pages all \
  --ocr \
  --tessdata-dir tessdata \
  --out out/gikaihi.all.json
```

## 使い方（財政全体像: naiyo-setsumei）

```bash
mkdir -p out
python3 parse_overview_pdf.py /path/to/naiyo-setsumei.pdf --out out/naiyo-setsumei.json
```

## ブラウザで見る（試作ビューア）

- 事業費別詳細: `viewer/index.html`
- 財政全体像: `viewer/overview.html`

どちらも「JSONファイルをファイル入力から選択」する方式なので、基本的にサーバ不要です。

## 注意
- このプロジェクトは `pdftotext -layout` を使ったヒューリスティック抽出です。PDFの作りによっては表の復元が崩れます。
- 出力JSONやPDFは大きくなりがちなので、このリポジトリではデフォルトでgit管理しない設定（`.gitignore`）にしています。
