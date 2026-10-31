# gikaihi.all.json レビュー（pdftotext方式・追加改善対象）

対象:

- PDF: `NIHO/gov/gikaihi.pdf`（110ページ）
- 出力JSON: `NIHO/gov/gikaihi.all.json`
- 生成スクリプト: `NIHO/gov/parse_budget_pdf.py`

このメモは、ユーザー指摘（p.18/p.20/p.75/p.77/p.81/p.85 など）を起点に、
現状の `gikaihi.all.json` に残っている誤りの傾向、原因、改善方針を整理したもの。

---

## 0) 改善後の結果（最新版 / 反映済み）

`NIHO/gov/parse_budget_pdf.py` の改善を反映して `NIHO/gov/gikaihi.all.json` を再生成した結果、ユーザー指摘の主要パターンは以下の通り改善できた。

### 0-0. 「事業費が間違っている」場合のフォールバックを追加（今回の追加点）

今回の運用要件（Webでの表示は厳密でなくてOK、一般財源でもOK）に合わせ、`budget.total` に対して **誤抽出の検知と補正（フォールバック）** を実装した。

- `budget.total_raw`: 事業費テーブル（pdftotext）から抽出した生値
- `budget.general_raw`: 一般財源（pdftotext）から抽出した生値
- `budget.details_sum`: 予算内訳（`budget_details`）の金額合計（S）
- `budget.total_display`: UI表示用の推定事業費
- `budget.total_display_source`: `details_sum` / `general` / `table_total` など
- `budget.total`: downstreamの混乱を避けるため、基本的に `total_display` で上書き（生値は `total_raw` に残す）

補正ルール（概要）:

- まず `details_sum`（S）が十分に取れている場合（S>=100 かつ欠損が少ない）を「信頼できる」とみなす
- そのとき `abs(total_raw - details_sum) > max(50, 0.05*S)` なら、`total` は誤抽出と判定して `total_display = details_sum` に切り替える
- `details_sum` が弱い場合は `general_raw` を次善策として採用（今回の要件上OK）

UI/QA用フラグ:

- `total_mismatch_details`: `total_raw` と `details_sum` に大幅乖離
- `general_mismatch_details`: `general_raw` と `details_sum` に大幅乖離
- `total_display_is_fallback`: 事業費が `details_sum` / `general` で補正されている

### 0-1. 重点ページの改善結果（例）

- p.18 検査事務
  - `budget.total`: **86**
  - `budget_details`: `11節/11節/14節` を復元（`＞` 混入なし）
- p.20 広聴事業
  - `budget.total`: **171**
  - `budget_details`: `8節/11節/14節` の3項目を復元（`＞` 混入なし）
  - `14節` 金額が欠けるケースは `total - 既知合計` で **自動補完**（例: 82）
- p.81 職員給与費
  - `name`: **職員給与費**
  - `department`: **職員課**
- p.85 市民税賦課事務
  - `budget.total`: **44,556**（`budget_details` 合算から推定）
  - `く予算内訳＞` マーカーが無いページでも、`1節/2節/…` 形式から内訳抽出して復元

### 0-2. 全体指標（今回の改善で確認できた範囲）

- `type=project` の `budget.total == null` は **0ページ**（欠損解消）
- `budget_details` への `＞` / `>` 混入は **0ページ**（除去）
- `給与費` 系ページの「担当課が `対象となる職員` に化ける」などの結合誤りは **解消**

### 0-3. まだ残り得る課題（次の改善候補）

- `（款）（項）（目）` の抽出が崩れて `type` が `unknown` になるページが一部ある（ヘッダー行の崩壊）
- `budget.revenue.general` は列判定の揺れで誤る場合がある（列位置の推定が完全ではない）
- `budget_details` に、ラベル欠損（例: `◇`）などのノイズが残るページがある（pdftotext由来）

---

## 1) 現状の観測（何が起きているか）

### 1-1. 事業費（budget.total）が入っていないページがある

現状、`type=project` のうち `budget.total == null` が複数ページで発生。

主に以下のパターンが原因:

- **小さい金額（例: 171千円）**が、PDF抽出で `1` + `71` のように分割され、既存の「カンマ付き数値抽出」に引っかからない
- 「（単位：千円）」直後の事業費テーブルが装飾罫線や縦積み数字になっており、通常の正規表現で拾えない

例:
- p.20 広聴事業（正解: 171千円）で `budget.total` が欠損していた
- p.18 検査事務でも `budget.total` が欠損していた

### 1-2. 予算内訳（budget_details）に「＞」が混入する

現状、`budget_details` の先頭に `{"item": "＞", "amount": ...}` のような行が混ざるケースがある。

原因:
- PDFの見出しが `く予算内訳＞` のように抽出され、解析の開始点をずらしても `＞` が残る
- その直後に数字だけの行が出ると、パーサが「＞」を項目名と誤認して金額を付与してしまう

例:
- p.18 検査事務: `item: "＞"` が内訳に混入
- p.20 広聴事業: 同様に `item: "＞"` が混入

### 1-3. 事業名に余計な記号・数字が混入する

現状、事業名に以下の“ノイズ先頭”が付くケースがある。

- 先頭が数字: `1 人権啓発事業` / `1 旧華頂宮邸管理運営事業`
- 先頭がローマ数字/区切り: `I 市民税賦課事務`
- 先頭が装飾記号: `︑ ｀ 川喜多映画記念館等管理運営事業`
- 行の取り違えで「担当課/該当ページ行」まで事業名に混入: `… 職員課 1 】 令和…`

原因:
- PDF由来の装飾行（ローマ数字/段番号/記号）が「事業名の前」に独立行として出る
- `_parse_name_department` のフォールバックが、候補行を誤って結合することがある

---

## 2) ユーザー指摘の具体例（現状の失敗モード）

### p.20 公聴（広聴）事業

期待:
- 事業費合計: **171千円**
- 予算内訳: 3項目
  - 8節 保育ボランティア謝礼
  - 11節 消耗品費
  - 14節 一日市長体験車両賃借料（等）

現状の問題:
- `budget.total` が null
- `budget_details` の先頭に `＞` が混入
- 14節が落ちたり、金額が取り違えたりする

原因仮説:
- 「（単位：千円）」直後の `1` + `71` のような分割を合成できていない
- `く予算内訳＞` の `＞` が残っている
- ラベル無しの数字行（例: `902`）が “金額の先行行” として混入し、誤関連付けを誘発

### p.18 検査事務

現状の問題:
- `budget.total` が null
- 予算内訳に `＞` が混入

原因仮説:
- 事業費テーブルの数値が縦積み or 小さな値で、既存ロジックでは拾えない
- 見出し末尾の `＞` を除去できていない

### p.75 / p.72 / p.85 / p.81 等（名前ノイズ）

現状の問題:
- 先頭に `1` / `I` / `︑ ｀` 等が付く
- 給与費ページで `職員給与費` が `9 職員給与費 …` のようになる可能性

原因仮説:
- PDF装飾（段番号/ローマ数字）が事業名行に混ざる
- 事業名の正規化が不足（先頭ノイズ除去）

---

## 3) 改善方針（pdftotextで直せる範囲）

### 3-1. 「事業費欠損」は要修正フラグ＋復元を入れる

- `budget.total` が取れない場合は `quality_flags` に `missing_budget_total` を追加
- 可能なら次の優先で復元:
  1) 「（単位：千円）」近傍の文字列から、空白除去後に `171` のような数値を拾う（分割数字の合成）
  2) それでも無理なら `sum(budget_details.amount)` を採用（推定）し、`budget.inferred_from_details=true` を付ける

### 3-2. 「＞混入」は budget_details パースのスキップルールを追加

- `＞`（単独、または `訳＞` など）を “スキップ対象行” として除外する
- 「ラベル無し数字行」は、最初の節ラベルが出るまでは捨てる（p.20の `902` 対策）

### 3-3. 「事業名に数字/|/装飾記号が混入」は正規化する

- `name` の先頭に以下が連続する場合は除去:
  - 数字だけのトークン（`1`、`9` 等）
  - ローマ数字 `I`、区切り `|`
  - 装飾記号（`︑`、`｀` 等）
- `name` に `令和` や `該当ページ` が混入している場合は、それより前で切る

---

## 4) 改善が難しい場合の方針（Cloud Vision等）

pdftotextで「表の数字が完全に崩壊している」ページは、OCR＋座標復元の方が有利な場合がある。
ただし今回 `gikaihi.pdf` は既にOCR済みの可能性が高く、再OCRはむしろノイズになりやすい。

推奨:
- pdftotextで **全体を正**にする
- “要修正フラグが立ったページだけ” v2のGCS非同期PDF入力（座標付きOCR）で再処理する（ハイブリッド）

---

# rodohi / gikaihi 共通メモ（quality_flags と mismatch の扱い）

rodohi（`NIHO/gov/rodohi.pdf` → `NIHO/gov/rodohi.all.json`）も gikaihi と同様に、`quality_flags` に
`total_mismatch_details` / `general_mismatch_details` / `total_display_is_fallback` が一定数出る。

結論としては、Web表示やランキング/ソートの実務要件（「厳密一致より見やすさ優先」）なら、
**金額は `budget.total_display`（= 実質 `budget.total`）を正として扱う前提でOK**。

## なぜ mismatch が出るのか（想定原因）

このスクリプトは `pdftotext -layout` の文字列を、表の列/予算内訳をヒューリスティックで復元しているため、
以下のいずれかで `total_raw`（表抽出）と `details_sum`（内訳合計）がズレる。

1. 表（事業費/一般財源）の列推定が崩れ、`total_raw` / `general_raw` 側が誤る
2. 予算内訳のパースが崩れ、`details_sum` 側が誤る（行の誤結合/欠損など）
3. PDF自体が「表の合計」と「内訳合計」が一致しない構造（小計/端数/内訳に出ない項目など）

## 現状の運用指針（おすすめ）

- 金額の表示・並び替えは `budget.total_display` を使う（viewerもこの扱い）
- `budget.total_display_source` を保持して、補正の由来（`details_sum` / `general` / `table_total`）を追えるようにする
- `quality_flags` は QA/レビュー用として使い、`total_mismatch_details` が立っているページだけ後から重点確認する

## 改善案（コスト順）

### A. 現状前提で進める（低コスト・効果大）

- UIでは `total_display` を正として使い、`total_display_source` に応じたバッジ（例: 内訳合計/一般財源）を表示する
- `total_mismatch_details` / `general_mismatch_details` が立つページは「要確認」扱いにする

### B. pdftotextベースのまま局所改善（中コスト）

- `_parse_budget_heuristic()`（表の列推定）を、ヘッダー位置や列クラスタの安定化で改善する
- `_parse_budget_details()`（内訳復元）を、数量列や分割行の誤結合に強くする

### C. mismatchページだけ OCR を試す（中〜高コスト）

現状の `--ocr` は「空/短いページだけ」フォールバックする設計なので、
ズレが多いページ（=テキストは取れているが数値推定が崩れている）では OCR が発火しにくい。

改善するなら:
- mismatch判定が立ったページだけ OCR を追加で試し、スコアが良い方を採用する（`score_parse()` で比較）

ただし OCR は数字誤読もあるので、必ず改善するとは限らない。

### D. 座標ベース抽出へ（高コスト・根本解決寄り）

`pdfplumber` / `pymupdf` 等で座標（x,y）を用いて表/内訳を列単位で抽出できると、崩れ耐性が上がる。
一方で依存追加と実装コストは大きいので、フェーズ次第で検討する。
