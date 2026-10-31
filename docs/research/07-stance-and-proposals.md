# 調査メモ 07: スタンス表明・コメント・市民発の提案の設計

作成 2026-10-31。拡充版 v2 の「スタンプ」「意見」「市民の提案」の根拠。[n] は末尾の URL。「要確認」は検索要約のみ・本文未読。推測は担当の推論。

## 要点

- 鎌倉の既存の入口は、陳情（誰でも出せるが審査されるとは限らない）、「わたしの提案」（個別回答）、Liqlid（市が決めたテーマのみ）。**自分で立てた提案に賛同が集まり、議員・市の反応が一覧で見える場は無い。**
- 海外の「閾値＋回答義務」型は、閾値到達が 2〜4%、到達後も実現は少数。**効くのは状態の見える化と「回答なし」の表示。**
- 法的な主リスクは公職選挙法（選挙運動・人気投票の公表・署名・18 歳未満）と個人情報（信条）。

## 事例

### 軽い表明
- **Yahoo! ニュース**: 2023-12 に「そう思う／そう思わない」を「共感した／なるほど／うーん」へ変更。賛否形式は感情が二極化し極端に捉えられるため [1]。AI 運営は非表示が導入 2 か月で 216 記事 [2]、投稿前の添削で不快コメント約 24% 減・投稿数は不変 [3]、2026-06 に論点をグラフ化する「ヤフコメまとめ」[4]。
- **Pol.is**: 返信不可・匿名・賛成/反対/パス [6]。台湾 UberX は 4,500 人超が 145 意見に投票 [7]。日本の世論地図（2024 衆院選）は約 2 週間で UU 4,403 人、ユーザー投稿は受けず人手レビュー [8]。米 Bowling Green は約 8,000 人・1 か月 [6][9]。
- Decidim Barcelona のコメント賛否タグ: 中立 63%／賛成 32%／反対 4.9%。反対タグが議論を起こしやすい [10]。

### 地域規模
- 加古川 Decidim: 登録 2,970 人（2024-03）→ 4,691 人（2025-02）、約 7 割が若年 [12]。世田谷の試行: 骨子 85 人 66 件、素案 4 人 6 件。テーマが広いと意見交換にならず行政回答も遅い [13]。甲賀市 Liqlid: 高校経由で 456 人 4,157 件、一般は計 24 件 [14]。鎌倉 Liqlid: 環境計画は 621 件・660 件（付箋を含む）[16]。

### 市民提案・請願（海外）
- **台湾 Join**: 60 日で 5,000 人 → 機関が 2 か月以内に回答。開始 5 年で 9,000 件超 → 成案 202（5% 未満）[17]。回答期限は多くの部会が守れず [18]。
- **韓国**: 青瓦台請願（30 日で 20 万人）は 111 万件中 285 件が到達。国民調査で 41.4% が「攻撃と嫌悪」、2022 年に終了 [19]。
- **英国**: 10,000 で政府回答、100,000 で討論検討。2011〜19 年に 56.3% を却下（重複が 52.3%）、100,000 到達は 0.15% [21]。
- **Madrid**: 支持 1% で住民投票。到達は約 26,000 件中 2 件、類似提案で支持が分散、市は提案へのフィードバック不可 [22][23]。
- **Better Reykjavik**: 毎月上位 15 件を市が処理（採択義務なし）、累計 70,000 人（人口の 58%）[24]。**エストニア**: 1,000 人で国会へ、委員会は 6 か月以内に決定 [26]。

### 国内
- **杉並区 参加型予算**: R5 は 57 件 → 10 事業 → 6,991 票 → 3 事業 [27]、R6 は 83 件 → 10 事業 → 3,322 人・8,749 票 → 3 事業（計 4,346 万円）[28]。
- **東京都 都民提案**: R6 は 854 件 → 13 件が投票（15 歳以上・3 票）[29]。
- **鎌倉「わたしの提案」**: 誰でも可、回答は原則文書でおおむね 2 週間、要旨を公表することがある [31]。
- **鎌倉の陳情**: 国籍・住所・年齢不問、紹介議員不要、FAX/メール不可、連名不可（代表 1 名）、定例会初日前日まで、住所氏名つきで公開、提出者は委員会で 10 分発言可 [32][33]。令和 7 年 2 月は 21 件、同 12 月は請願 2＋陳情 19、**令和 8 年 9 月は請願 1＋陳情 54 件**（配付 10・付託 44: 採択 4／不採択 13／継続 16／議決不要 11）[36]。配付のみの基準は「市外郵送・既結論と同趣旨・市の事務外」等 [37]。
- 横浜市会は陳情をオンライン提出可（R6 は 83 件中 31.3%）[39]。

## スタンス表明の型（軽い → 重い）

| 型 | 内容 | 長所 | 短所 | 向く議題 |
|---|---|---|---|---|
| A ひとこと反応 | 共感した／なるほど／うーん | 1 タップで二極化を避ける | 賛否にならない | 議案・陳情の全件 |
| B 立場＋理由 | 賛成／反対／まだ決められない ＋ 理由 1 つ。鎌倉市民確認済みのみ集計、市外は別枠 | 議員・市に示せる数字になる | 自己選択バイアス、組織票 | 重要議案・陳情・市民提案 |
| C 意見地図 | Pol.is 型。期間 2〜4 週、声明 20〜40 本 | 返信なしで荒れにくく、合意点が見える | 声明の中立な選定に人手 | 新庁舎のような対立の深い争点 |
| D 理由つき議論 | 賛否タグつきコメント（Kialo 型） | 論点の深さ | 運営負荷が最大、過疎、荒れ | 期間限定の少数テーマ |

- 実名／匿名: 匿名可の新聞コメントは非礼 53.3%、実名/Facebook 28.7% [42]。韓国の実名制は発言数を減らしたが抑止は限定的で 2012 年に違憲・廃止 [43]。炎上の書込み経験者は約 1.5% で少数が繰り返す [43]。→ 本人確認は実名・表示名は選択制、初回投稿の制限（Discourse の信頼レベル [44]）、ルールの固定表示（r/science で新規の遵守 +8pt [45]）、投稿前の添削、期間・テーマの限定を組み合わせる。

## 市民の提案: 状態遷移と鎌倉の閾値（推測を含む）

- 状態: ① 確認中（重複・市の事務か・誹謗でないかを数営業日で。却下は理由を公開）→ ② 賛同募集（30〜60 日。鎌倉市民確認済みのみ計上）→ ③ 回答依頼（閾値到達で自動送付）→ ④ 回答あり／期限切れ（**「回答なし」も表示**）→ ⑤ 陳情提出（番号・付託先）→ ⑥ 審査結果（採択／不採択／継続／議決不要）→ ⑦ 市の対応（検討／実施／見送り＋理由）。
- 閾値案（有権者 147,351 人・議員定数 26・最下位当選 1,329 票 [48]）: **回答依頼 = 賛同 30**（約 0.02%、Join・英国と同水準）、**陳情化の支援 = 100〜150**、公開質問・特集 = 300〜740（0.5%）、約 1,470（1%）超 = 住民投票条例の直接請求（有権者の 1/50 ≒ 約 3,000 筆・紙の署名）を検討。
- 現実的な参加数: 登録は人口の 1〜2%、投票は 0.6%（杉並 R6）。1 提案の賛同は 10〜100 が標準、数百は例外、千超は市役所移転級。
- 回答役: 市は「わたしの提案」が 2 週間で回答する前例 [31] があるが覚書がなければ義務なし。**議員 26 名に同一の質問票（賛成／反対／保留＋一言）を送り、期限は議員 14 日・市 30 日を提示、無回答も表示。** 運営は中継と記録に徹する。
- 陳情への接続: FAX/メール不可・連名不可・署名簿は直筆のため、サイトは下書き生成、配付基準のチェック、代表 1 名での提出、賛同数の参考添付（受理可否は議会事務局に要確認）、10 分発言の支援、結果の反映を担う。
- 荒れ・乗っ取り: 重複統合と類似提案の事前提示、住所確認による 1 人 1 賛同、テーマを絞る、公開カウントの遅延表示。

## 法的・運用上の注意

- **選挙運動**: 特定の選挙で特定候補の当選を目的とする行為。政策への賛否集計は政治活動の範囲と考えられるが、選挙期間中に候補者名と賛否を結んで投票先を示唆する表示は避ける（推測）[49]。
- **138 条の 3**: 当選予想の人気投票の公表は禁止（ネット上も）[50]。候補者名を選ぶ投票は作らない。
- **138 条の 2**: 投票を得る目的の署名運動は禁止。任期満了選挙では直接請求の署名運動が 60 日前から禁止 [51]。**機能名は「署名」でなく「賛同」。**
- **18 歳未満**の選挙運動は禁止（137 条の 2）。議題への意見は可、候補者応援は不可 [52]。
- **ボートマッチ型の「議員との一致度」**: 杉並区選管は 2023 年に総務省の技術的助言で中止 [53]。市・選管と共催せず、選挙期間中は表示停止を検討。
- **個人情報**: 「信条」は要配慮個人情報 [54]。個人名つきの賛否は既定で出さず、出すなら明示同意。
- 陳情書は住所氏名つきで公開される [32] ため、陳情化の際は提案者へ事前に説明する。

## 未確認

- 加古川の提案 517 件／採択 25 件（確認できたのは「政策作成プロセス 25 件」）、Yahoo コメント反応の参加率、小規模自治体の Decidim/Consul の採択率、円ベースの運営費、Join の最新統計と ID 認証の一次情報、鎌倉の「わたしの提案」の年間件数、Liqlid の実名／匿名ルール。鎌倉の陳情が令和 8 年 9 月に 54 件と直前の約 2.5 倍になった理由。

## 出典（抜粋）

- [1] https://www.lycorp.co.jp/ja/news/release/001004/ ／ [2] https://webtan.impress.co.jp/n/2022/01/21/42237 ／ [3] https://www.lycorp.co.jp/ja/news/release/016951/ ／ [4] https://webtan.impress.co.jp/n/2026/06/30/52888 ／ [6] https://en.wikipedia.org/wiki/Pol.is ／ [7] https://www.bertelsmann-stiftung.de/en/our-projects/democracy-and-participation-in-europe/shortcut-archive/shortcut-8-trailblazers-of-digital-participation-taiwans-join-platform-and-vtaiwan ／ [8] https://scrapbox.io/nishio/世論地図2024振り返り ／ [10] https://arxiv.org/pdf/1707.06526
- [12] https://www.mlit.go.jp/toshi/tosiko/content/001892577.pdf ／ [13] https://www.city.setagaya.lg.jp/documents/10991/3.pdf ／ [16] https://www.city.kamakura.kanagawa.jp/kankyo/seisaku/documents/20260323shiryou1-1.pdf
- [17] https://news.pts.org.tw/article/491166 ／ [18] https://tdr.lib.ntu.edu.tw/handle/123456789/74489 ／ [19] https://www.fnnews.com/news/202204201143157319 ／ [21] https://revues.u-bordeaux-montaigne.fr/leaves/article/download/12/920?inline=1 ／ [22] https://participedia.net/case/6895 ／ [23] https://blog.thegovlab.org/learning-from-decide-madrid ／ [24] https://citizens.is/blog/citizens-foundation-main-projects/ ／ [26] https://www.riigikogu.ee/en/introduction-and-history/have-your-say/submit-collective-proposal/
- [27] https://www.city.suginami.tokyo.jp/s001/1436.html ／ [28] https://www.city.suginami.tokyo.jp/s001/17433.html ／ [29] https://www.metro.tokyo.lg.jp/information/press/2024/07/2024072606 ／ [31] https://www.city.kamakura.kanagawa.jp/soudan/goiken_goteian.html ／ [32] https://www.city.kamakura.kanagawa.jp/gikai/documents/seigan-tinzyotebiki.pdf ／ [33] https://www.city.kamakura.kanagawa.jp/gikai/tinzyou2.html ／ [36] https://www.city.kamakura.kanagawa.jp/gikai/202609gikai.html ／ [37] https://www.city.kamakura.kanagawa.jp/gikai/documents/20251201haifukijyun.pdf ／ [39] https://www.city.yokohama.lg.jp/shikai/kiroku/katsudo/r7/ShikaiunneiR07.files/U-20250925-5.pdf
- [42] https://sciencedaily.com/releases/2014/01/140122134310.htm ／ [43] https://www.soumu.go.jp/iicp/chousakenkyu/data/research/icp_review/11/11-4yamaguchi2015.pdf ／ [44] https://meta.discourse.org/t/understanding-discourse-trust-levels/90752 ／ [45] https://www.inverse.com/article/55348-r-science-experiment-community-guidelines-prevent-harassment ／ [46] https://docs.decidim.org/en/admin/components/proposals/answers ／ [48] https://go2senkyo.com/local/senkyo/21904
- [49] https://www.city.sapporo.jp/senkan/internet.html ／ [50] https://www.ben54.jp/news/1612 ／ [51] https://www.city.okayama.jp/0000011132.html ／ [52] https://www.ben54.jp/news/3999 ／ [53] https://www.city.suginami.tokyo.jp/documents/4977/sozai050222-7.pdf ／ [54] https://www.ppc.go.jp/personalinfo/legal/guidelines_tsusoku/ ／ [57] https://docs.consuldemocracy.org/docs_general/participation-processes/citizen-proposals ／ [59] https://www.city.kamakura.kanagawa.jp/gikai/documents/gikaikihonjoureihyoukakensyoukyougikaihoukokusyo2.pdf

## 追記: ソシオクラシー（同意型）の参考（owner 2026-10-31 提示）

- 記事: IDEAS FOR GOOD「決め手は“好きか”より“許容範囲か”」（2026-10-22、ロンドンの労働者協同組合 Outlandish の事例） https://ideasforgood.jp/2026/10/22/outlandish-sociocracy/
- 仕組み: 多数決でも全員賛成でもなく **同意（consent）** = 重大な異議がなければ進む。「同意とは受け入れることであって、賛成することではない」。提案は「何を／なぜ／いつ／誰が／いくら」の 5 項目。3 ラウンド（確認の質問 → 最初の反応 → 重大な懸念の有無）。異議には根拠と解決案が要り、懸念は案を強くする行為と位置づける。サークル（領域ごとの意思決定チーム）、発言は輪番・パス可。「good enough for now, safe enough to try」。
- サイトへの応用（v2 モックで「同意型」として実装）: スタンプを「異議なし／懸念あり／異議（理由と代案）」の 3 つにし、「好きかどうかでなく受け入れられるか」を問う。懸念は一覧にして「同じ懸念なら押す」で束ね、市の考えを懸念ごとに返す。提案フォームは 5 項目の型。読む会を「懸念を順番に話す 3 ラウンド」の場にする。
- 注意: 記事の事例は小規模（メンバー 4 人）。「全員いいえで通過」は大規模だと少数の異議で止まりうるので、Web では「懸念の束ね」と「返事」に使い、決定の規則そのものにはしない（推測）。
