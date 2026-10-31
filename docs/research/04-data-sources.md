# 調査メモ 04: 鎌倉市の一次データの入口

作成 2026-10-31。gikai.niho.life が読む元データの所在と、取れる・取れないの整理。

## 議会

| 種類 | 所在 | 分かっていること |
|---|---|---|
| 会議録の検索 | https://www.kensakusystem.jp/kamakura/index.html | 外部システム。本会議録は平成 13 年（2001）5 月以降、委員会議録は平成 17 年（2005）1 月以降。閲覧と検索。 |
| 本会議の録画 | https://www.kensakusystem.jp/kamakura-vod/index.html | 専用システム（YouTube ではない）。日程・議員名・キーワードで検索。委員会が対象かは未確認。市の公式 YouTube は別にある（未確認）。 |
| 議案と結果 | 定例会ごとの市ページ（例: 令和 8 年 9 月定例会 https://www.city.kamakura.kanagawa.jp/gikai/202609gikai.html ） | 市長提出・議員提出の議案と結果（「原案可決（賛成多数）」など集計表記）。**議員ごとの賛否は公開されていない。** 議員提出議案は議案集 https://www.city.kamakura.kanagawa.jp/gikai/gikaigiansyuu.html （平成 28 年〜、PDF）。 |
| 請願・陳情 | 同じ定例会ページ | 令和 8 年 9 月定例会は請願 1 件、陳情第 20〜73 号（54 件）。提出方法 https://www.city.kamakura.kanagawa.jp/gikai/tinzyou2.html |
| 議員・会派 | https://www.city.kamakura.kanagawa.jp/gikai/shigikaigiin.html | 議員 25 名（定数 26）。会派 7（自民党・無所属の会、鎌倉前進の会、公明党、夢みらい鎌倉、公正と法、日本共産党、立憲民主党）＋無所属 4。委員会構成は役員名簿 PDF。 |
| 議会だより | https://www.city.kamakura.kanagawa.jp/gikai/tayori/202611gikaidayori.html | 最新は第 275 号（令和 8 年 11 月 1 日）。 |
| 定例会の日程 | https://www.city.kamakura.kanagawa.jp/gikai/nenkanyotei.html | 定例会は 6・9・12・2 月。臨時会あり。 |
| 議会報告会 | https://www.city.kamakura.kanagawa.jp/gikai/kamando2026.html | 未読。 |
| 市議会トップ | https://www.city.kamakura.kanagawa.jp/gikai/ | |

## 予算・決算・財政

| 種類 | 所在 | 分かっていること |
|---|---|---|
| 予算の入口 | https://www.city.kamakura.kanagawa.jp/shisei/yosan/index.html | 入口一覧のみ。年度別 https://www.city.kamakura.kanagawa.jp/shisei/yosan/nendobetsu/index.html （未読）。 |
| 財政課 | https://www.city.kamakura.kanagawa.jp/zaisei/ | 自動取得は 403（ブラウザでは開く想定）。 |
| 予算書 PDF（令和 7 年度） | hihirohub `download-hi/gov/*.pdf` に保存済み | 事業費別詳細（議会費・労働費・消防費・民生費）、`naiyo-setsumei.pdf`（総括表・性質別）、歳入。→ `05-existing-assets.md` |
| 決算 | 定例会ページ | 令和 7 年度一般会計決算は 2026-09-30 に原案認定（賛成多数）。 |
| オープンデータ | https://www.city.kamakura.kanagawa.jp/opendata/opendata.html | 自動取得は 403。予算・議会のデータセットの有無は未確認。指針 PDF https://www.city.kamakura.kanagawa.jp/opendata/documents/opendata-guideline_1.pdf |

## 令和 7 年度 一般会計 当初予算（抽出済みの実数）

歳出 809.7 億円（前年 744.6 億円）。款別（億円・構成比・前年差）:

| 款 | 億円 | 構成比 | 前年差 |
|---|---:|---:|---:|
| 民生費 | 331.3 | 40.9% | +25.9 |
| 土木費 | 122.9 | 15.2% | +17.9 |
| 総務費 | 101.3 | 12.5% | +21.1 |
| 衛生費 | 87.2 | 10.8% | +18.1 |
| 教育費 | 78.6 | 9.7% | −8.6 |
| 公債費 | 36.8 | 4.5% | −4.4 |
| 消防費 | 30.8 | 3.8% | −5.5 |
| 農林水産業費 | 5.9 | 0.7% | +4.3 |
| 商工費 | 4.8 | 0.6% | +0.2 |
| 議会費 | 4.4 | 0.5% | +0.0 |
| 観光費 | 4.1 | 0.5% | −3.7 |
| 労働費 | 0.9 | 0.1% | +0.0 |
| 予備費 | 0.5 | 0.1% | +0.0 |
| 諸支出金 | 0.1 | 0.0% | +0.0 |

歳入は市税 385.9 億円（47.7%）が最大。性質別（人件費・物件費・扶助費・補助費等・建設事業費…）の款×性質の表も抽出済み。

## 取れる・取れない（設計への含意）

- **取れる**: 会議録の全文（本会議 25 年分・委員会 21 年分）、録画の検索、議案の件名と結果、陳情の件名と結果、議員と会派、予算書 PDF（構造化は自前）。
- **取れない（市が出していない）**: 議員別の賛否、予算の CSV。賛否は会議録本文の「起立」「採決」から復元できる可能性があるが、記名採決でない限り会派単位の推定になる。
- **留意**: 会議録は検索システムからの取得（スクレイピングの可否・利用条件は未確認）。録画の埋め込み可否も未確認。市への相談で「データ提供（CSV・API）」を引き出せると運用が軽くなる。
