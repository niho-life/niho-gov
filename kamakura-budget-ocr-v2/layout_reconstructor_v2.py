"""
改善版レイアウト復元モジュール
KMeansクラスタリングによる列推定 + 詳細な信頼度計算
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

import config


@dataclass
class Word:
    """座標付き単語"""
    text: str
    left: int
    top: int
    right: int
    bottom: int
    confidence: float = 1.0
    
    @property
    def width(self) -> int:
        return self.right - self.left
    
    @property
    def height(self) -> int:
        return self.bottom - self.top
    
    @property
    def center_x(self) -> int:
        return (self.left + self.right) // 2
    
    @property
    def center_y(self) -> int:
        return (self.top + self.bottom) // 2


@dataclass
class Line:
    """行（複数の単語を含む）"""
    words: List[Word] = field(default_factory=list)
    
    @property
    def text(self) -> str:
        return " ".join([w.text for w in sorted(self.words, key=lambda w: w.left)])
    
    @property
    def top(self) -> int:
        return min(w.top for w in self.words) if self.words else 0
    
    @property
    def bottom(self) -> int:
        return max(w.bottom for w in self.words) if self.words else 0
    
    @property
    def left(self) -> int:
        return min(w.left for w in self.words) if self.words else 0
    
    @property
    def right(self) -> int:
        return max(w.right for w in self.words) if self.words else 0
    
    @property
    def avg_confidence(self) -> float:
        if not self.words:
            return 0.0
        return sum(w.confidence for w in self.words) / len(self.words)


@dataclass
class TableCell:
    """表のセル"""
    text: str
    row: int
    col: int
    confidence: float = 1.0


@dataclass
class Table:
    """表"""
    cells: List[TableCell] = field(default_factory=list)
    rows: int = 0
    cols: int = 0
    
    def to_2d_array(self) -> List[List[str]]:
        """2次元配列に変換"""
        if not self.cells:
            return []
        
        array = [[""] * self.cols for _ in range(self.rows)]
        for cell in self.cells:
            if 0 <= cell.row < self.rows and 0 <= cell.col < self.cols:
                array[cell.row][cell.col] = cell.text
        return array


def parse_gcv_response(gcv_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    GCV非同期APIのレスポンスをパース
    
    Returns:
        ページごとの単語リスト
    """
    pages_data = []
    
    responses = gcv_json.get("responses", [])
    
    for response in responses:
        full_text_annotation = response.get("fullTextAnnotation", {})
        
        for page in full_text_annotation.get("pages", []):
            page_words = []
            page_width = page.get("width", 0)
            page_height = page.get("height", 0)
            
            for block in page.get("blocks", []):
                for paragraph in block.get("paragraphs", []):
                    for word in paragraph.get("words", []):
                        # テキスト結合
                        text = "".join([
                            s.get("text", "") for s in word.get("symbols", [])
                        ])
                        
                        # bbox取得
                        bbox = word.get("boundingBox", {})
                        vertices = bbox.get("vertices", [])
                        
                        if len(vertices) >= 4:
                            xs = [v.get("x", 0) for v in vertices]
                            ys = [v.get("y", 0) for v in vertices]
                            
                            page_words.append(Word(
                                text=text,
                                left=min(xs),
                                top=min(ys),
                                right=max(xs),
                                bottom=max(ys),
                                confidence=word.get("confidence", 1.0)
                            ))
            
            pages_data.append({
                "width": page_width,
                "height": page_height,
                "words": page_words
            })
    
    return pages_data


def group_words_into_lines(
    words: List[Word],
    page_height: int,
    y_threshold: int = None
) -> List[Line]:
    """
    y座標が近い単語を同一行にグルーピング
    
    Args:
        words: 単語リスト
        page_height: ページ高さ
        y_threshold: 同一行とみなすy座標の閾値（None時は自動計算）
    """
    if not words:
        return []
    
    # 閾値の自動計算
    if y_threshold is None:
        y_threshold = max(
            config.LINE_Y_THRESHOLD_MIN,
            int(page_height * config.LINE_Y_THRESHOLD_RATIO)
        )
    
    # top座標でソート
    sorted_words = sorted(words, key=lambda w: (w.top, w.left))
    
    lines = []
    current_line = Line(words=[sorted_words[0]])
    current_y = sorted_words[0].top
    
    for word in sorted_words[1:]:
        if abs(word.top - current_y) <= y_threshold:
            # 同一行に追加
            current_line.words.append(word)
        else:
            # 新しい行を開始
            lines.append(current_line)
            current_line = Line(words=[word])
            current_y = word.top
    
    # 最後の行を追加
    lines.append(current_line)
    
    return lines


def estimate_columns_kmeans(
    lines: List[Line],
    k_min: int = None,
    k_max: int = None
) -> Tuple[List[int], int]:
    """
    KMeansクラスタリングで列位置を推定
    
    Args:
        lines: 行リスト
        k_min: 最小列数
        k_max: 最大列数
    
    Returns:
        (列の左端x座標リスト, 選択されたk)
    """
    if k_min is None:
        k_min = config.COLUMN_K_MIN
    if k_max is None:
        k_max = config.COLUMN_K_MAX
    
    # 全単語の左端x座標を収集
    x_positions = []
    for line in lines:
        for word in line.words:
            x_positions.append(word.left)
    
    if len(x_positions) < k_min:
        return sorted(set(x_positions)), len(set(x_positions))
    
    X = np.array(x_positions).reshape(-1, 1)
    
    # 最適なkをsilhouetteスコアで選択
    best_k = k_min
    best_score = -1
    best_labels = None
    best_centers = None
    
    for k in range(k_min, min(k_max + 1, len(set(x_positions)) + 1)):
        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            
            if len(set(labels)) > 1:
                score = silhouette_score(X, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
                    best_labels = labels
                    best_centers = kmeans.cluster_centers_
        except Exception:
            continue
    
    if best_centers is None:
        return sorted(set(x_positions))[:k_max], k_min
    
    # クラスタ中心を列位置として返す
    column_positions = sorted([int(c[0]) for c in best_centers])
    
    return column_positions, best_k


def assign_words_to_columns(
    line: Line,
    column_positions: List[int]
) -> List[str]:
    """
    行内の単語を列に割り当て
    
    Returns:
        各列のテキスト（結合済み）
    """
    if not column_positions:
        return [line.text]
    
    cells = [""] * len(column_positions)
    
    for word in sorted(line.words, key=lambda w: w.left):
        # 最も近い列を見つける
        min_dist = float('inf')
        best_col = 0
        
        for i, col_x in enumerate(column_positions):
            dist = abs(word.left - col_x)
            if dist < min_dist:
                min_dist = dist
                best_col = i
        
        # 列に追加
        if cells[best_col]:
            cells[best_col] += " " + word.text
        else:
            cells[best_col] = word.text
    
    return cells


def reconstruct_table(
    lines: List[Line],
    start_idx: int,
    end_idx: int
) -> Table:
    """
    指定範囲の行から表を再構築
    
    Args:
        lines: 全行のリスト
        start_idx: 開始行インデックス
        end_idx: 終了行インデックス
    
    Returns:
        復元された表
    """
    table_lines = lines[start_idx:end_idx]
    
    if not table_lines:
        return Table()
    
    # 列位置を推定
    column_positions, k = estimate_columns_kmeans(table_lines)
    
    # 各行を列に割り当て
    cells = []
    for row_idx, line in enumerate(table_lines):
        row_cells = assign_words_to_columns(line, column_positions)
        for col_idx, cell_text in enumerate(row_cells):
            cells.append(TableCell(
                text=cell_text.strip(),
                row=row_idx,
                col=col_idx,
                confidence=line.avg_confidence
            ))
    
    return Table(
        cells=cells,
        rows=len(table_lines),
        cols=len(column_positions)
    )


def normalize_number(text: str) -> Optional[int]:
    """
    テキストから数値を正規化
    
    - 全角→半角
    - カンマ除去
    - △→マイナス
    """
    if not text:
        return None
    
    # 全角→半角
    text = text.translate(str.maketrans(
        '０１２３４５６７８９．，',
        '0123456789.,'
    ))
    
    # カンマ・スペース除去
    text = re.sub(r'[,，\s]', '', text)
    
    # △→マイナス
    text = text.replace('△', '-')
    
    # ドット区切りの数字を結合（24.310 → 24310）
    if re.match(r'^\d+\.\d+$', text):
        text = text.replace('.', '')
    
    # 数値として解釈
    try:
        return int(float(text))
    except ValueError:
        return None


def extract_amounts_from_line(line: Line) -> List[Tuple[str, int, float]]:
    """
    行から金額を抽出
    
    Returns:
        [(テキスト, 金額, 信頼度), ...]
    """
    amounts = []
    
    for word in line.words:
        amount = normalize_number(word.text)
        if amount is not None and amount > 0:
            amounts.append((word.text, amount, word.confidence))
    
    return amounts


def find_table_region(
    lines: List[Line],
    header_keywords: List[str] = None
) -> Optional[Tuple[int, int]]:
    """
    事業費テーブルの領域を検出
    
    Returns:
        (開始行インデックス, 終了行インデックス) or None
    """
    if header_keywords is None:
        header_keywords = config.TABLE_HEADER_KEYWORDS
    
    header_idx = None
    
    for i, line in enumerate(lines):
        line_text = line.text
        if any(kw in line_text for kw in header_keywords):
            header_idx = i
            break
    
    if header_idx is None:
        return None
    
    # テーブル終了位置を探す
    end_idx = len(lines)
    
    for i in range(header_idx + 1, len(lines)):
        line_text = lines[i].text
        
        # 「予算内訳」で終了
        if re.search(config.PATTERNS["detail_label"], line_text):
            end_idx = i
            break
        
        # 大きな空白で終了
        if i > 0:
            gap = lines[i].top - lines[i-1].bottom
            if gap > config.PARAGRAPH_GAP_THRESHOLD * 2:
                end_idx = i
                break
    
    return (header_idx, end_idx)


def extract_budget_details(
    lines: List[Line],
    start_idx: int
) -> List[Dict[str, Any]]:
    """
    予算内訳を抽出
    
    Args:
        lines: 全行のリスト
        start_idx: 「予算内訳」ラベルの行インデックス
    
    Returns:
        [{"section": int, "item": str, "amount": int, "confidence": float}, ...]
    """
    details = []
    current_section = None
    
    for i in range(start_idx, len(lines)):
        line = lines[i]
        line_text = line.text
        
        # ページ番号行はスキップ
        if re.match(r'^[\d\-\s]+$', line_text.strip()):
            continue
        
        # 節番号を検出
        section_match = re.search(config.PATTERNS["budget_detail_section_pattern"], line_text)
        if section_match:
            current_section = int(section_match.group(1))
        
        # 金額を抽出（行の右端）
        amounts = extract_amounts_from_line(line)
        if not amounts:
            continue
        
        # 最も右にある金額を採用
        rightmost_word = max(line.words, key=lambda w: w.right)
        amount = normalize_number(rightmost_word.text)
        
        if amount is None or amount == 0:
            continue
        
        # 項目名（金額以外の部分）
        item_words = [w for w in line.words if w != rightmost_word]
        item_text = " ".join([w.text for w in sorted(item_words, key=lambda w: w.left)])
        
        # 節番号を除去
        item_text = re.sub(r'^\d+節\s*', '', item_text).strip()
        
        # ゴミ文字を除去
        item_text = re.sub(config.PATTERNS["garbage"], '', item_text).strip()
        
        if not item_text:
            continue
        
        detail = {
            "item": item_text,
            "amount": amount,
            "line_confidence": line.avg_confidence
        }
        
        if current_section:
            detail["section"] = current_section
        
        # 数量を抽出（「1人」「24人」など）
        qty_match = re.search(r'(\d+[人回部式台ページ個件])', item_text)
        if qty_match:
            detail["quantity"] = qty_match.group(1)
        
        details.append(detail)
    
    return details


def calculate_field_confidence(
    words_or_lines: List[Any],
    field_name: str
) -> float:
    """
    フィールドの信頼度を計算
    """
    confidences = []
    
    for item in words_or_lines:
        if isinstance(item, Word):
            confidences.append(item.confidence)
        elif isinstance(item, Line):
            confidences.append(item.avg_confidence)
        elif isinstance(item, dict):
            confidences.append(item.get("confidence", item.get("line_confidence", 1.0)))
    
    if not confidences:
        return 0.0
    
    # 基本は平均値
    base_conf = sum(confidences) / len(confidences)
    
    # フィールド別の重みを適用
    weight = config.CONFIDENCE_WEIGHTS.get(field_name, 0.1)
    
    return base_conf


def process_page(
    page_data: Dict[str, Any],
    page_num: int
) -> Dict[str, Any]:
    """
    1ページを処理して構造化データを返す
    
    Args:
        page_data: パース済みページデータ（words, width, height）
        page_num: ページ番号
    
    Returns:
        構造化されたページデータ
    """
    words = page_data.get("words", [])
    page_height = page_data.get("height", 1000)
    page_width = page_data.get("width", 700)
    
    # 行にグルーピング
    lines = group_words_into_lines(words, page_height)
    
    # 全テキスト再構成
    full_text = "\n".join([line.text for line in lines])
    
    # CID問題検出
    has_cid_issue = bool(re.search(config.PATTERNS["cid_pattern"], full_text))
    
    # テーブル領域検出
    table_region = find_table_region(lines)
    table_data = None
    budget_total = None
    
    if table_region:
        table = reconstruct_table(lines, *table_region)
        table_data = table.to_2d_array()
        
        # 事業費（総額）を抽出
        for line in lines[table_region[0]:table_region[1]]:
            if "事業費" in line.text:
                amounts = extract_amounts_from_line(line)
                if amounts:
                    # 最大の金額を採用
                    budget_total = max(a[1] for a in amounts)
                    break
    
    # 予算内訳を抽出
    budget_details = []
    for i, line in enumerate(lines):
        if re.search(config.PATTERNS["detail_label"], line.text):
            budget_details = extract_budget_details(lines, i + 1)
            break
    
    # 内訳合計
    details_sum = sum(d["amount"] for d in budget_details) if budget_details else 0
    
    # 総合信頼度計算
    word_confidences = [w.confidence for w in words if w.confidence]
    avg_confidence = sum(word_confidences) / len(word_confidences) if word_confidences else 0.0
    
    result = {
        "page_number": page_num,
        "page_size": {"width": page_width, "height": page_height},
        "full_text": full_text,
        "lines": [
            {
                "text": line.text,
                "bbox": [line.left, line.top, line.right, line.bottom],
                "confidence": line.avg_confidence
            }
            for line in lines
        ],
        "table": table_data,
        "budget_total": budget_total,
        "budget_details": budget_details,
        "budget_details_sum": details_sum,
        "stats": {
            "line_count": len(lines),
            "word_count": len(words),
            "detail_count": len(budget_details),
            "avg_confidence": avg_confidence,
            "has_cid_issue": has_cid_issue
        }
    }
    
    return result


def process_gcv_output(
    gcv_json_path: Path,
    output_dir: Path
) -> List[Dict[str, Any]]:
    """
    GCV出力JSONを処理
    
    Args:
        gcv_json_path: GCV出力JSONのパス
        output_dir: 出力ディレクトリ
    
    Returns:
        処理された全ページのデータ
    """
    print(f"📐 レイアウト復元: {gcv_json_path.name}")
    
    with open(gcv_json_path, "r", encoding="utf-8") as f:
        gcv_json = json.load(f)
    
    # ページごとの単語を抽出
    pages_data = parse_gcv_response(gcv_json)
    
    results = []
    for i, page_data in enumerate(pages_data):
        page_num = i + 1  # 1-indexed
        
        print(f"  処理中: ページ {page_num}")
        
        structured = process_page(page_data, page_num)
        results.append(structured)
        
        # 個別ページを保存
        page_output = output_dir / f"page_{page_num:03d}_structured.json"
        with open(page_output, "w", encoding="utf-8") as f:
            json.dump(structured, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 完了: {len(results)}ページ処理")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python layout_reconstructor_v2.py <gcv_json_path>")
        sys.exit(1)
    
    gcv_path = Path(sys.argv[1])
    results = process_gcv_output(gcv_path, config.OCR_STRUCTURED_DIR)
    
    # サマリー出力
    print(f"\n📊 サマリー:")
    print(f"   ページ数: {len(results)}")
    print(f"   平均信頼度: {sum(r['stats']['avg_confidence'] for r in results) / len(results):.2%}")
    print(f"   CID問題: {sum(1 for r in results if r['stats']['has_cid_issue'])}ページ")
