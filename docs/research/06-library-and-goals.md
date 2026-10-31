# 調査メモ 06: 議題の資料を束ねる「資料室」と、街の目標の見せ方

作成 2026-10-31。拡充版 v2 の「資料室」「街のこれから」の根拠。[n] は末尾の URL。「検索抜粋」は本文を直接取得できず検索結果の要約だけで書いた箇所。

## 結論

- 自治体議会は「会期単位の PDF／表」で、**議案・議題単位に資料を束ねた例は国内に見つからなかった**（横浜・大津・鎌倉）。国会だけが議案単位の経過ページを持つ。手本は海外: Legistar（議案）、Decidim（プロセス）、英国 Commons Library と国立国会図書館（中立の解説）。
- 鎌倉は素材の大半が公開済みだが、観光課・総務課・議会・企画課・外部システムに散在。薄いのは **委員会の審査（資料・結果）と会派別の賛否**。
- 鎌倉の第 4 次総合計画は **施策 43・指標 138**。目標の多くは数値でなく「目指す向き（⇗）」で、R8〜R12 の実績欄は空。進捗は「基準値からの推移と向き」で見せるのが実態に合う。

## 事例（束ねるもの／更新／評価）

- **Legistar / Councilmatic**（米）: 1 件の議案（matter）に添付・履歴・提出者・本文の版・関連議案が付き、議題項目に採決・出欠が付く [1][2]。Councilmatic は同じ API の市民向け画面（OSS・変更通知、Seattle 版は AI 要約）[4][5]。データモデルの手本だが解説はない。
- **Decidim**: 時系列のフェーズ（紹介→診断→提案→優先→評価→モニタリング）× 部品（会議・提案・結果・Accountability）[6][7]。説明・期間・現フェーズ・統計・文書を 1 ページに束ねる [8]。議題ページに最も近いが運営コストが大きい。
- **英国 Commons Library**: 約 350 トピック × 種別 × 日付、政府法案ごとに briefing（人手）[47][49]。**国立国会図書館 Issue Brief**: 1 号 1 テーマ・10 頁前後・ほぼ週 1 回 [9]。構成は「要点 3 行 → 概要 → 論点（有識者の見解を並置）→ 脚注」[10]。中立な解説の手本。
- **国内**: 国会は提出→付託→審査→議決→賛成・反対会派→公布を 1 表に [11]。横浜は定例会別の議案ページ＋別ページの賛否 PDF（議員別は令和 2 年〜）[12][13]、大津は年度別の議案一覧＋会期ごとの賛否 PDF [14]。委員会記録・録画まで議案別に束ねる例はなし。
- 週次フィード型（米の地域メディア「今週の市役所」）: 機関別の見出し＋日時＋議題 1 行の平易な要約＋公式リンク [45][46]。日本の「今週の市政」型は見つからず。

## 議題ページに置く資料の種類（出どころ／鎌倉での入手）

| 種類 | 出どころ | 鎌倉 |
|---|---|---|
| 議案本文・補正予算の説明書 | 総務課・議会 | ○ 定例会単位の PDF（その 1 は 74 頁、差し替え版あり）。議案別は自前で分割 [19][20]。提案理由は条例案にだけ付く |
| 付託先・議決結果・議決日、請願・陳情の結果 | 議会 | ◎ HTML 表 [17]（陳情の本文は見つからず） |
| 会派・議員別の賛否 | 議会 | × 見つからず（横浜・大津は公開） |
| 委員会の資料・結果 | 所管課・議会 | △ 委員会ページに PDF リンク 0 [21] |
| 質疑・答弁 | 外部システム | ○ 会議録 H13〜 [23]。録画は日程／議員名／検索で入り、議案単位の入口なし [22] |
| 一般質問の通告・文書質問 | 議会 | ○ 通告 PDF [17]、答弁書は R8 年度 18 件 [24] |
| 予算・決算 | 財政課 | ○ 説明書 PDF [35]、**オープンデータあり** [36] |
| 市の計画・指標・実施計画・行政評価 | 企画課 | ◎ [25][31][32] |
| パブコメ・審議会・検討委員会 | 所管課 | ○ 課ごとに散在、一覧なし [33][34]。総合計画審議会は 11 回分の次第・資料・議事録が揃う [29] |
| 報道・市民の声 | — | 別途 |
| 年表 | 自動 | 日付から機械的に組める。例「宿泊税」: 検討委員会 2/10 → 報告書 6 月 → 制度案・意見公募 6/8〜7/8 → 議案第 46 号 提出 9/2 → 総務常任委員会 9/15 → 可決（賛成多数）9/30（2026 年）[56][37][20][21][17] |

## 街の目標と進捗の見せ方（型 5）

1. **施策シート型**: 目標→取組→事業→指標→予算・実績を 1 枚に。鎌倉の施策 5-5「広聴」は「意見を届けられている市民の割合 7.3%（2025・市民意識調査・⇗）」「参画を実感 31.4%」＋R8〜R12 の実績欄 [28]。
2. **実感×客観の並置型**: 指標 138 本の 32%（44 本）が市民意識調査 [27]。将来目標を「そう思う市民の割合」で測る（住み続けたい 81.3%、豊かで安全 39.2% など）[26]。
3. **約束の漏斗型**（提案→見解→決定→実施）: Decidim Accountability は実施率 0〜100% [7]、バルセロナは 1,400 超の行動の進捗を公開 [43]、マドリードは閾値到達の提案に 30 日以内の回答義務＋追跡タブ（検索抜粋）[51]。
4. **予算ドリルダウン型**: 計画→事業→予算（横浜の財政ダッシュボードは予算事業ごとのページ 1,840 本＋提案ボタン）[41]。
5. **週次フィード型**: 上記。

総合計画 KPI を市民向けに出す国内ダッシュボード（会津若松・神戸・福岡）は見つからず。Japan Dashboard・地域課題ダッシュボードは国の統計の比較で、計画の進捗ではない [39][40]。旧計画の行政評価は PDF（指標 106 本中 48 達成、外部評価あり）[31]。

## 所見（鎌倉の規模で現実的な範囲）

- 市長提出議案は定例会あたり 28 件前後、陳情 54 件（R8.9）[17]。全件の手作りは非現実的。**編集する議題を年 10〜20 本＋残りは自動生成の薄いページ、の二層**が妥当。
- 自動取得しやすいもの: 定例会の表・議案集 PDF（目次で分割できる）・審議会ページ・通告／答弁書 PDF。PDF は差し替え版が出る（版管理が要る）。委員会審査と賛否は公開が薄く、会議録・録画待ちか人手。外部システムの規約は未確認。
- **施策番号（43）を議題の親にすると目標と議会の動きがつながる**（例: 宿泊税→3-11 観光、広聴→5-5）。
- 重複注意: 市は Liqlid で意見募集を運用（総合計画の意見公募 143 件中 Liqlid 89 件）[30]。7.3% は市の指標で、NIHO の声の数とは定義が違うので混ぜない。

## 未確認

- 取得不可（検索抜粋）: 英国 Parliament 系、TheyWorkForYou、Decide Madrid、Decidim Barcelona、札幌・取手。Legistar と国会の議案ページの実画面。
- 見つからず: 会津若松・神戸・福岡の計画 KPI 公開、鎌倉の会派別賛否・パブコメ一覧・委員会資料の所在、43 施策 PDF の URL 規則（確認できたのは広聴 5-5 と観光 3-11）。

## 出典（抜粋）

- [1] https://webapi.legistar.com/Help ／ [2] https://legistar.council.nyc.gov/Legislation.aspx ／ [3] https://intro.nyc/1446-2025+ ／ [4] https://datamade.us/our-work/councilmatic/nyc-council-councilmatic ／ [5] https://civictech.guide/projects/seattle-councilmatic
- [6] https://docs.decidim.org/en/admin/spaces/processes/phases ／ [7] https://docs.decidim.org/en/features/components ／ [8] https://meta.decidim.org/processes/roadmap?locale=en
- [9] https://www.ndl.go.jp/jp/diet/publication/issue/index.html ／ [10] https://dl.ndl.go.jp/view/prepareDownload?itemId=info:ndljp/pid/15019906 ／ [11] https://www.shugiin.go.jp/internet/itdb_gian.nsf/HTML/gian/keika/1DE2176.htm
- [12] https://www.city.yokohama.lg.jp/shikai/kiroku/kekka/gianR08-4.html ／ [13] https://www.city.yokohama.lg.jp/shikai/kiroku/kekka/kaihabetsu.html ／ [14] https://www.city.otsu.lg.jp/gikai/nittei/74068.html
- 鎌倉: [17] https://www.city.kamakura.kanagawa.jp/gikai/202609gikai.html ／ [19] https://www.city.kamakura.kanagawa.jp/soumu/202609teireikai.html ／ [20] https://www.city.kamakura.kanagawa.jp/soumu/documents/giannsyuusono1.pdf ／ [21] https://www.city.kamakura.kanagawa.jp/gikai/080915soumu.html ／ [22] https://www.kensakusystem.jp/kamakura-vod/index.html ／ [23] https://www.kensakusystem.jp/kamakura/index.html ／ [24] https://www.city.kamakura.kanagawa.jp/gikai/r08d_bunsyositumon.html ／ [25] https://www.city.kamakura.kanagawa.jp/keiki/4th-plan/main.html ／ [26] https://www.city.kamakura.kanagawa.jp/keiki/4th-plan/documents/vision2034tougoubannp6_p9.pdf ／ [27] https://www.city.kamakura.kanagawa.jp/keiki/4th-plan/documents/kamakuravision2034tougoubannp171_p177.pdf ／ [28] https://www.city.kamakura.kanagawa.jp/keiki/r8-newmp/documents/miraikyosoplan2030_5_5_kocho.pdf ／ [29] https://www.city.kamakura.kanagawa.jp/keiki/r8-newmp/soukeisin.html ／ [30] https://www.city.kamakura.kanagawa.jp/keiki/r8-newmp/documents/0220250530.pdf ／ [31] https://www.city.kamakura.kanagawa.jp/keiki/hyouka/documents/97r7matome.pdf ／ [32] https://www.city.kamakura.kanagawa.jp/keiki/r8-newmp/jissiplan.html ／ [33] https://www.city.kamakura.kanagawa.jp/shisei/shisaku/index.html ／ [34] https://www.city.kamakura.kanagawa.jp/jimukan/shingikai.html ／ [35] https://www.city.kamakura.kanagawa.jp/zaisei/second-08.html ／ [36] https://www.city.kamakura.kanagawa.jp/opendata/opendata.html ／ [37] https://www.city.kamakura.kanagawa.jp/kankou/documents/seidoannituite-02.pdf ／ [56] https://www.city.kamakura.kanagawa.jp/kankou/documents/01siryou1.pdf
- [39] https://www.digital.go.jp/resources/japandashboard ／ [40] https://www.chisou.go.jp/sousei/about/dashboard/index.html ／ [41] https://prtimes.jp/main/html/rd/p/000000843.000013670.html ／ [43] https://beteve.cat/politica/pam-decidim-barcelona/ ／ [44] https://council.nyc.gov/pb/ ／ [45] https://raincrossgazette.com/this-week-in-city-hall-june-10-2024 ／ [46] https://theraleighcommons.org/raleighpublicrecord/topics/agenda-preview/
- 検索抜粋のみ: [47] https://commonslibrary.parliament.uk/the-legislative-process-and-library-briefings-on-bills/ ／ [49] https://researchbriefings.parliament.uk/ ／ [51] https://diario.madrid.es/decidemadrid/2017/12/20/como-seguir-el-estado-de-los-proyectos-de-presupuestos-participativos-en-decide-madrid/ ／ [53] https://www.govtech.com/dc/a-look-at-new-york-citys-participatory-budgeting-map.html
