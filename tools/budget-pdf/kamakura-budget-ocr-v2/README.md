# 鎌倉市予算書OCRパイプライン v2.0

自治体予算書PDF（日本語）を高精度に構造化JSONデータに変換するパイプライン。

## 特徴

- **GCS経由の非同期処理**: 大量ページを安定して処理
- **KMeansクラスタリング**: 表の列位置を自動推定
- **Document AIフォールバック**: 低信頼ページを自動で再処理
- **詳細な検証ロジック**: 予算合計チェック、自動補正、フラグ付け
- **中間成果物の保存**: パーサー改良時にOCR再実行不要

## アーキテクチャ

```
PDF
 ↓
① GCSアップロード
 ↓
② Vision API 非同期バッチOCR（座標付きテキスト）
 ↓
③ レイアウト復元（KMeansで列推定、行・表再構築）
 ↓
④ JSON変換（款項目・事業名・予算抽出）
 ↓
⑤ 自動検証 + フラグ付け
 ↓
⑥ [オプション] Document AIで低信頼ページを再処理
 ↓
⑦ 最終JSON/JSONL/CSV出力
```

## セットアップ

### 1. 前提条件

```bash
# macOS
brew install poppler

# Ubuntu
sudo apt install poppler-utils
```

### 2. Python環境

```bash
# 仮想環境を作成（推奨）
python -m venv venv
source venv/bin/activate

# パッケージインストール
pip install \
    google-cloud-vision \
    google-cloud-storage \
    google-cloud-documentai \
    pdf2image \
    opencv-python \
    pillow \
    numpy \
    pandas \
    scikit-learn \
    tqdm
```

### 3. GCP設定

#### 3.1 プロジェクト作成
1. [GCPコンソール](https://console.cloud.google.com/) でプロジェクト作成
2. Billing を有効化

#### 3.2 API有効化
```bash
gcloud services enable vision.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable documentai.googleapis.com  # オプション
```

#### 3.3 GCSバケット作成
```bash
# 入力バケット
gsutil mb -l asia-northeast1 gs://kamakura-budget-input

# 出力バケット
gsutil mb -l asia-northeast1 gs://kamakura-budget-output
```

#### 3.4 サービスアカウント作成
```bash
# サービスアカウント作成
gcloud iam service-accounts create sa-ocr \
    --display-name="OCR Service Account"

# 権限付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:sa-ocr@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:sa-ocr@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/vision.admin"

# キー作成
gcloud iam service-accounts keys create credentials.json \
    --iam-account=sa-ocr@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### 3.5 環境変数設定
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/credentials.json"
export GCP_PROJECT_ID="your-project-id"
export GCS_INPUT_BUCKET="kamakura-budget-input"
export GCS_OUTPUT_BUCKET="kamakura-budget-output"

# .bashrc / .zshrc に追加
cat >> ~/.zshrc << 'EOF'
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
export GCP_PROJECT_ID="your-project-id"
export GCS_INPUT_BUCKET="kamakura-budget-input"
export GCS_OUTPUT_BUCKET="kamakura-budget-output"
EOF
```

#### 3.6 [オプション] Document AI設定
```bash
# Document AIコンソールでプロセッサ作成
# https://console.cloud.google.com/ai/document-ai

# プロセッサIDを環境変数に設定
export DOCUMENT_AI_PROCESSOR_ID="your-processor-id"
```

## 使い方

### 基本実行（全工程）

```bash
# PDFをinputディレクトリに配置
mkdir -p input
cp /path/to/議会費.pdf input/

# パイプライン実行
python pipeline.py input/議会費.pdf
```

### ローカルモード（GCSを使わない）

GCSを使わずにローカルで処理する場合：

```bash
python pipeline.py input/議会費.pdf --local
```

### 特定ステップのみ実行

```bash
# アップロードのみ
python pipeline.py input/議会費.pdf --step upload

# OCRのみ（アップロード済み前提）
python pipeline.py input/議会費.pdf --step ocr

# パースのみ（OCR済み前提）
python pipeline.py input/議会費.pdf --step parse

# JSON変換のみ（パース済み前提）
python pipeline.py input/議会費.pdf --step convert

# Document AI再処理のみ
python pipeline.py input/議会費.pdf --step retry
```

### コスト確認（ドライラン）

```bash
python pipeline.py input/議会費.pdf --dry-run
```

## 出力構造

```
output/
└── {job_name}_{timestamp}_{run_id}/
    ├── ocr_raw/                    # GCV生出力
    │   ├── output-1-to-20.json
    │   └── output-21-to-40.json
    ├── structured/                 # 構造化済み
    │   ├── page_001_structured.json
    │   └── ...
    ├── final/                      # 最終出力
    │   ├── kamakura_budget_YYYYMMDD_HHMMSS.json
    │   ├── kamakura_budget_YYYYMMDD_HHMMSS.jsonl
    │   └── kamakura_budget_review_YYYYMMDD_HHMMSS.json
    └── logs/
        └── {run_id}.json
```

## 最終JSONスキーマ

```json
{
  "metadata": {
    "municipality": "鎌倉市",
    "fiscal_year": 2025,
    "budget_type": "一般会計",
    "extraction_method": "Google Cloud Vision API (Async Batch)",
    "pipeline_version": "v2.0",
    "extracted_at": "2025-01-15T12:00:00Z",
    "validation_summary": {
      "total": 100,
      "valid": 92,
      "with_flags": 8,
      "auto_corrected": 3,
      "needs_review": 5
    }
  },
  "projects": [
    {
      "id": "R07-05-05-05-003",
      "text_hash": "a1b2c3d4",
      "source_page": 3,
      "confidence": 0.92,
      "category": {
        "kuan": {"code": 5, "name": "議会費"},
        "kou": {"code": 5, "name": "議会費"},
        "moku": {"code": 5, "name": "議会費"}
      },
      "name": "議会事務",
      "department": "議会総務課・議事調査課",
      "type": "normal",
      "purpose": {
        "target": "市議会議員等",
        "intent": "市議会の円滑な運営と活性化...",
        "effect": "市民の声を反映した政策の実現..."
      },
      "description": ["...", "..."],
      "budget": {
        "total": 295014,
        "total_from_details": 295014,
        "unit": "千円",
        "revenue": {
          "national_prefectural": 0,
          "local_bond": 0,
          "other": 0,
          "general": 295014
        }
      },
      "budget_details": [
        {
          "section": 1,
          "item": "議長報酬",
          "quantity": "1人",
          "amount": 6987,
          "line_confidence": 0.95
        }
      ],
      "prev_year_page": "P11-P12",
      "validation": {
        "is_valid": true,
        "flags": [],
        "messages": [],
        "auto_corrected": false
      }
    }
  ]
}
```

## 検証フラグ

| フラグ | 意味 | 対応 |
|--------|------|------|
| `sum_mismatch` | 予算合計と内訳合計が不一致 | 自動補正 or レビュー |
| `low_confidence` | OCR信頼度が75%未満 | Document AI再処理 |
| `missing_name` | 事業名が抽出できない | レビュー |
| `missing_department` | 担当課が抽出できない | レビュー |
| `missing_budget` | 事業費が抽出できない | レビュー |
| `cid_detected` | PDFフォント問題 | Document AI再処理 |

## コスト

| サービス | 料金 | 備考 |
|----------|------|------|
| Vision API | $1.50/1000ページ | 月1000ページ無料 |
| Document AI | $1.50/1000ページ | Form Parser |
| Cloud Storage | $0.02/GB/月 | 最小限 |

**110ページの場合**:
- Vision API: ~$0.17（無料枠超過分）
- Document AI (10%再処理): ~$0.02
- **合計: ~$0.20**

## トラブルシューティング

### 認証エラー
```
google.auth.exceptions.DefaultCredentialsError
```
→ `GOOGLE_APPLICATION_CREDENTIALS` 環境変数を確認

### GCSアクセス拒否
```
403 Forbidden
```
→ サービスアカウントの権限を確認（`storage.objectAdmin`）

### OCRタイムアウト
→ `config.py` の `VISION_TIMEOUT` を延長

### 予算内訳が取れない
1. `ocr_raw/*.json` で座標を確認
2. `config.py` の `LINE_Y_THRESHOLD_*` を調整
3. Document AI再処理を有効化

### 列がずれる
→ `config.py` の `COLUMN_K_MIN`, `COLUMN_K_MAX` を調整

## 開発

### ファイル構成

```
kamakura-budget-ocr-v2/
├── config.py                 # 設定（GCP、閾値、パターン）
├── pipeline.py               # メインパイプライン
├── gcs_vision_client.py      # GCS + Vision API非同期処理
├── layout_reconstructor_v2.py # KMeansによるレイアウト復元
├── json_converter_v2.py      # 検証付きJSON変換
├── docai_fallback.py         # Document AIフォールバック
└── README.md
```

### パーサー改良時

OCR結果は `ocr_raw/` に保存されているので、
パーサーだけ修正して再実行：

```bash
python pipeline.py input/議会費.pdf --step parse --step convert
```

### 検証ルールの調整

`config.py` の以下を調整：
- `CONFIDENCE_THRESHOLD_AUTO_OK`: 自動OKの閾値
- `CONFIDENCE_THRESHOLD_REVIEW`: レビュー必須の閾値
- `BUDGET_TOLERANCE_PERCENT`: 予算合計誤差の許容範囲

## 運用フロー（推奨）

1. **パイロット**: 10ページでテスト
2. **全体実行**: 全ページをOCR
3. **自動検証**: フラグ付きレコードを確認
4. **Document AI**: 低信頼ページを再処理
5. **人手レビュー**: `*_review_*.json` を確認・修正
6. **データ投入**: Notion/スプレッドシート/DBへ

## ライセンス

MIT

## 参考

- [Google Cloud Vision API](https://cloud.google.com/vision/docs)
- [Google Document AI](https://cloud.google.com/document-ai/docs)
- [pdfplumber vs pdftotext比較](https://github.com/jsvine/pdfplumber)
