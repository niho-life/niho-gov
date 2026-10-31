# gikaihi.pdf 実行レビュー（pdftotext方式改善版 vs kamakura-budget-ocr-v2）

対象PDF: `NIHO/gov/gikaihi.pdf`（110ページ）

このレビューは、同一PDFに対して以下2つを実際に実行した結果の記録と評価です。

- **pdftotext（埋め込みテキスト）方式**: `NIHO/gov/parse_budget_pdf.py`
- **OCR + 座標復元方式（v2）**: `NIHO/gov/kamakura-budget-ocr-v2/`（Vision API）

前提: `gikaihi.pdf` は `pdfinfo` 上 `Adobe Acrobat Standard ... Paper Capture Plug-in` 由来で、既にOCR済みPDFの可能性が高いです。  
このタイプは「さらにOCRで取り直す」より「埋め込みテキストを抽出する」方が正確になりやすいです。

---

## 1) 起きた結果（実行ログ）

### 1-1) pdftotext方式（改善版）

- 出力JSON: `NIHO/gov/gikaihi.all.json`
- 実行（例）:
  - `python3 NIHO/gov/parse_budget_pdf.py NIHO/gov/gikaihi.pdf --pages all --ocr --tessdata-dir NIHO/gov/tessdata --out NIHO/gov/gikaihi.all.json`
  - ※ `--ocr` は “pdftotextが空/極端に短いページ” のみフォールバック（全ページOCRではない）

改善で直った代表例:
- p.23（以前は `name="】"`、金額が `1` になる問題）
  - `name`: 建築等紛争調整事業
  - `department`: 地域共生課
  - `prev_year_page`: P31
  - `budget_details` の `1 + 24 -> 124` の復元を実装して修正

### 1-2) v2（Vision API OCR）方式

実行はできました（認証OK）。ただし結果の品質は低いです。

- 最新出力ディレクトリ:
  - `NIHO/gov/kamakura-budget-ocr-v2/output/gikaihi_20251227_033952_b8f09d/`
- 出力（最終JSON）:
  - `NIHO/gov/kamakura-budget-ocr-v2/output/gikaihi_20251227_033952_b8f09d/final/gikaihi_20251227_034110.json`
  - `NIHO/gov/kamakura-budget-ocr-v2/output/gikaihi_20251227_033952_b8f09d/final/gikaihi_review_20251227_034110.json`
- 実行モード:
  - `--local`（PDF→画像→Vision同期APIでOCR）を使用

なお、v2パイプラインのログ保存で `PosixPath is not JSON serializable` が発生していたため、修正して完走できるようにしました:
- 修正: `NIHO/gov/kamakura-budget-ocr-v2/pipeline.py`

---

## 2) 評価（精度）

### 2-1) v2の自己評価（validation）

v2の出力JSON（`gikaihi_20251227_034110.json`）に含まれる `validation_summary` は以下でした。

- 総数: 109
- 有効: 3（2.8%）
- 要レビュー: 109
- フラグ内訳:
  - `low_confidence`: 109
  - `missing_budget`: 106
  - `missing_name`: 12
  - `missing_department`: 10

結論: **今回のPDFに対して v2（ローカルOCRモード）は、現状のままでは採用不可**です。  
理由は、予算書として最重要の「事業費/財源/予算内訳」の抽出に大きく失敗しているためです。

### 2-2) “改善済みpdftotext JSON”の精度見積もり（%）

ユーザー判断のため、評価軸を明確に分けます。

対象: `NIHO/gov/gikaihi.all.json`

#### (A) 抽出できた `project` の中での精度（Precision寄り）

`type=project` は 62ページ。

- 事業同定の必須（`category` + `name` + `department`）が揃う率: **62/62 = 100%**
- `prev_year_page` が有効（空や `P` だけでない）: **54/62 = 87.1%**
- `budget_details` が1件以上: **51/62 = 82.3%**
- `purpose` が入る: **48/62 = 77.4%**
- `description` が入る: **51/62 = 82.3%**

→ 「抽出できた事業だけ先に見せる」なら十分実用レベルです（事業名/担当課が壊れないのが強い）。

#### (B) PDF全体に対するカバレッジ（Recall寄り）

- 全110ページのうち `project` と判定できたページ: **62/110 = 56.4%**
- `unknown` が 45ページあり、現状は “全事業を網羅” できていません。

#### 90%超え判定について

「90%OK」をどの軸で見るかで結論が変わります。

- **事業同定（name/department/category）だけの品質**なら: 100%（OK）
- **PDF全体（全事業網羅）**なら: 56%（NG）

市民公開で「全事業を見せたい」なら後者が重要なので、現状では **90%未達**と判断します。  
一方で「まず見える範囲から公開し、unknownを後で埋める」なら、前者で進めるのは現実的です。

---

## 3) 原因分析（なぜv2の精度が低かったか）

主因は v2 の設計思想と今回のPDF構造（および実行モード）のミスマッチです。

### 3-1) 既にOCR済みPDFを「画像→OCR」で取り直した

既に埋め込みテキストがあるPDFに対して再OCRすると、

- 文字間に空白が入る（日本語が “分かち書き” っぽくなる）
- 記号（◎、【】、縦棒、ローマ数字I）が壊れる/欠ける
- 数字・カンマが崩れる

が起きやすく、正規表現や表復元が難しくなります。

### 3-2) `--local` はPDF入力の非同期OCRより情報が落ちやすい

PDF→画像化は dpi/画質の影響が大きく、表の罫線や列境界が弱いと列推定が崩れます。
今回の `missing_budget` 大量発生は、この影響が濃厚です。

### 3-3) 予算抽出ロジックがOCRテキストの揺れに耐えられていない

`missing_budget` が 106/109 ということは、
budget抽出をテキストベースで拾う前提（見出しや表のキーワード）に、OCR結果が合っていない可能性が高いです。

---

## 4) 改善案（次にやるべきこと）

### 4-1) 推奨: ハイブリッド運用（最短で本番に近づく）

- **正（source of truth）**: `NIHO/gov/gikaihi.all.json`（pdftotext方式）
- v2は “怪しいページだけ” に限定して使う
  - `unknown` ページ
  - `quality_flags` が多いページ（例: `tiny_amount_rows` が多い、など）

これがコスト/精度/運用のバランスが最も良いです。

### 4-2) v2を改善して再挑戦するなら

- `--local` ではなく、README通り **GCS非同期（PDF入力）経路**で回す（安定しやすい）
- ローカルOCRを使うなら、PDF→画像化のdpi調整・言語ヒントの強制などを入れて改善する
- budget抽出は “復元テーブル（structured）” を主に参照するよう改善する（OCRテキストからの一本釣りを減らす）

### 4-3) pdftotext方式で“全事業カバレッジ90%”を目指すなら

現状の最大ボトルネックは `project coverage`（56%）なので、以下が最優先です。

- `unknown` ページを分類し、なぜ `project` 判定に落ちるか特定する
- `project` 判定を「category + 事業名候補 + 【担当課】」など複数条件で拾う（`◎` に依存しすぎない）

---

## 5) セキュリティ注意（credential）

サービスアカウントキー（credential JSON）は秘密鍵です。

- リポジトリにコミットしない
- できればリポジトリ外（例: `~/keys/...`）に置く
- 本作業では `.gitignore` へ除外を追加済み

