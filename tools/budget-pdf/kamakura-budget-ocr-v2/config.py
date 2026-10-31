"""
鎌倉市予算書OCRパイプライン - 設定ファイル（完全版）
GCS非同期処理 + Document AIフォールバック対応
"""
from pathlib import Path
import os

# === GCPプロジェクト設定 ===
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "kamakura-budget")
GCP_LOCATION = "us"  # Document AI用

# === GCS バケット設定 ===
GCS_INPUT_BUCKET = os.getenv("GCS_INPUT_BUCKET", "kamakura-budget-input")
GCS_OUTPUT_BUCKET = os.getenv("GCS_OUTPUT_BUCKET", "kamakura-budget-output")
GCS_OUTPUT_PREFIX = "vision-results/"

# === ローカルパス設定 ===
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
OCR_RAW_DIR = OUTPUT_DIR / "ocr_raw"
OCR_STRUCTURED_DIR = OUTPUT_DIR / "ocr_structured"
FINAL_DIR = OUTPUT_DIR / "final"
LOGS_DIR = BASE_DIR / "logs"
REVIEW_DIR = OUTPUT_DIR / "review"

# ディレクトリ作成
for d in [INPUT_DIR, IMAGES_DIR, OCR_RAW_DIR, OCR_STRUCTURED_DIR, FINAL_DIR, LOGS_DIR, REVIEW_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# === Vision API設定 ===
VISION_BATCH_SIZE = 20  # 1出力ファイルあたりのページ数
VISION_TIMEOUT = 1800   # 30分
VISION_MAX_RETRIES = 3

# === Document AI設定（フォールバック用） ===
DOCUMENT_AI_PROCESSOR_ID = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
DOCUMENT_AI_ENABLED = bool(DOCUMENT_AI_PROCESSOR_ID)

# === OCR設定 ===
OCR_LANGUAGE_HINTS = ["ja"]

# === 信頼度設定 ===
CONFIDENCE_THRESHOLD_AUTO_OK = 0.85  # これ以上なら自動OK
CONFIDENCE_THRESHOLD_REVIEW = 0.75   # これ未満はレビュー必須
CONFIDENCE_WEIGHTS = {
    "name": 0.15,
    "department": 0.10,
    "budget_total": 0.35,
    "budget_details": 0.30,
    "purpose": 0.10
}

# === 検証設定 ===
BUDGET_TOLERANCE_PERCENT = 0.01  # 1%
BUDGET_TOLERANCE_MIN = 1  # 最小1千円

# === レイアウト復元設定 ===
# 行結合: y座標がこの範囲内なら同一行（ページ高さの0.8%または固定8px）
LINE_Y_THRESHOLD_RATIO = 0.008
LINE_Y_THRESHOLD_MIN = 8

# 列推定: KMeansのk範囲
COLUMN_K_MIN = 2
COLUMN_K_MAX = 8

# 段落区切り
PARAGRAPH_GAP_THRESHOLD = 40

# === 表検出設定 ===
TABLE_HEADER_KEYWORDS = ["事業費", "国県支出金", "地方債", "その他", "一般財源"]
BUDGET_DETAIL_SECTION_PATTERN = r"(\d+)節"

# === フラグ定義 ===
FLAG_SUM_MISMATCH = "sum_mismatch"
FLAG_LOW_CONFIDENCE = "low_confidence"
FLAG_MISSING_NAME = "missing_name"
FLAG_MISSING_DEPARTMENT = "missing_department"
FLAG_MISSING_BUDGET = "missing_budget"
FLAG_PARSE_ERROR = "parse_error"
FLAG_CID_DETECTED = "cid_detected"  # PDFフォント問題

# === メタデータ ===
METADATA = {
    "municipality": "鎌倉市",
    "fiscal_year": 2025,
    "fiscal_year_japanese": "令和7年度",
    "budget_type": "一般会計",
    "extraction_method": "Google Cloud Vision API (Async Batch)",
    "pipeline_version": "v2.0"
}

# === 正規表現パターン ===
PATTERNS = {
    # 款/項/目
    "category_full": r'（款）\s*([0-9０-９]+)\s*(\S+?)（項）\s*([0-9０-９]+)\s*(\S+?)（目）\s*([0-9０-９]+)\s*(\S+)',
    "kuan_only": r'（款）\s*([0-9０-９]+)',
    
    # 担当課
    "department": r'([^\n]{1,40}(?:課|局|部|室))',
    "department_bracket": r'【(.+?)】',
    
    # 金額
    "amount": r'([△\-\d\，,０-９\.]+)\s*$',
    "amount_normalize": r'[,，\s]',
    
    # セクションラベル
    "purpose_label": r'事業の目的|【事業の目的】',
    "content_label": r'事業の内容|【事業の内容】',
    "budget_label": r'事業費|（単位：千円）|（単位•千円）',
    "detail_label": r'予算内訳|く予算内',
    
    # 前年度ページ
    "prev_year": r'令和\d+年度該当ページ[：:]\s*(.+?)(?=\n|【|$)',
    
    # ゴミ文字
    "garbage": r'[r゜゛―贔冒．I\f]+',
    
    # CID問題検出
    "cid_pattern": r'\(cid:\d+\)'
}

# === コスト見積もり ===
# GCV: $1.50/1000ページ（最初の1000ページ/月は無料）
# Document AI: $1.50/1000ページ（Form Parser）
COST_PER_1000_PAGES_GCV = 1.50
COST_PER_1000_PAGES_DOCAI = 1.50
