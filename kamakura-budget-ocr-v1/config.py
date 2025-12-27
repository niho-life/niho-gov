# config.py
# 基本設定。必要に応じて上書きしてください。
INPUT_BUCKET = "kamakura-budget-input"
OUTPUT_BUCKET = "kamakura-budget-output"
GCV_OUTPUT_PREFIX = "vision-results/"
LOCAL_WORKDIR = "./output"
BATCH_SIZE = 20
TIMEOUT_SECONDS = 3600

# layout
PAGE_Y_TOLERANCE_RATIO = 0.008

# validation
MIN_CONFIDENCE_RECORD = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.75

# output files
FINAL_JSON = f"{LOCAL_WORKDIR}/final/kamakura_budget.json"
OCR_RAW_DIR = f"{LOCAL_WORKDIR}/ocr_raw"
PARSED_DIR = f"{LOCAL_WORKDIR}/parsed"
STRUCT_DIR = f"{LOCAL_WORKDIR}/struct"
LOG_DIR = f"{LOCAL_WORKDIR}/logs"
