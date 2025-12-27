# kamakura-budget-ocr

GCV（Google Cloud Vision）を使って鎌倉市の予算PDFを全ページOCR → 事業単位JSONへ変換するワークフロー。

## 概要
- 非同期 GCV (`asyncBatchAnnotateFiles`) を用いて PDF を GCS に送信
- GCV 出力 JSON をダウンロード・正規化（word + bbox + conf）
- 行結合・テーブル復元（座標クラスタリング）
- 事業単位にセグメント化して JSON に変換
- 自動検証（合計チェック・confidence）→ フラグ化
- フラグレコードは簡易レビュワで確認・編集可能

## セットアップ
1. GCP プロジェクトを作成し、Cloud Vision API を有効化
2. service account を作り JSON キーをダウンロードして `credentials.json` として配置
3. バケットを作成:
   - `kamakura-budget-input` （PDF をアップロード）
   - `kamakura-budget-output` （GCV 出力 JSON）
4. Python 環境を整え、依存をインストール:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 実行（パイロット）
```bash
# 環境変数
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

# PDF をアップロード
gsutil cp input/議会費_sample5.pdf gs://kamakura-budget-input/議会費_sample5.pdf

# パイプライン実行（例）
python ocr_pipeline.py \
  --gcs_input gs://kamakura-budget-input/議会費_sample5.pdf \
  --gcs_output_prefix gs://kamakura-budget-output/vision-results-test/ \
  --local /tmp/kamakura_test
```

## 実行（本番）
同様に `--gcs_input` に本番PDFを指定して実行してください。

## レビュワUI
```bash
FLASK_APP=review_ui.py flask run --host=0.0.0.0 --port=5000
```
レビュワは `output/final/kamakura_budget.json` と `output/ocr_raw/` を参照します。

## 注意
- 最初は小規模（5–10 ページ）で検証・閾値調整してください
- Document AI による差分再処理は別モジュール化予定（必要時対応）
