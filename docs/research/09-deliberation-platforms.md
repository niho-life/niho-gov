# 調査メモ 09: 熟議プラットフォームの事例と、案を磨く場の設計

作成 2026-10-31。owner の方針「市民から市への要望ではなく、街の人どうしが議論して案を磨く熟議の場」の根拠。v2 モックの最初の形は軽い投稿とコメントだけで、ここに書く「案を比べる・磨く」は応用機能（後の段階）。[U] は末尾の URL。推測は担当の推論。

## 要点

- 案を磨いた実績は **「無作為抽出＋少人数＋中立な情報＋決まった出口」の対面型** に厚い。オンラインは束ねる・比べる・修正する役。
- 鎌倉に同型の先例がある: **脱炭素かまくら市民会議**（2024.10〜2025.1、約 2,500 通 → 回答 358 → 46 人・全 4 回、10 のアクションを実際に試してから議論、成果は市民自身／地域主体／行政の 3 層・48 取組み、2025-03-04 に市長へ手交）[U20][U21][U22]。

## 事例

### オンライン
- **Consider.it**（米 WA 州の住民投票、2012）: 賛否の理由を並べ、他人の理由を自分の欄へ取り込む。5〜6 週で訪問 8,813 人、立場の 41.4% が賛否両方を記述。利用者がリベラルに偏り、最難関は「どの理由を信じるか」[U1]。
- **Loomio**: 提案へ賛成／保留／反対／ブロック。ブロックは再検討を強制。オンラインの個人拒否権は危険（既存の信頼関係が前提）[U2][U3]。
- **Kialo**: 賛否ツリー。折衷案を置けず、反論が埋もれる [U4]。
- **Your Priorities / Better Reykjavik**: 利用 7 万人（人口の 58%・運営の自己申告）。My Neighbourhood は案投稿 1 か月 → 市が費用と実現可能性を確認 → 予算超過は選べない投票 [U5][U6]。
- **広聴 AI / Talk to the City**: 東京都は 2050 戦略で AI が 27,915 件を分析し政策体系を再編。チームみらいは 8,559 提案から 254 件採用。限界 = 大クラスタ ≠ 重要、ブラックボックスだと「捨てられた」感、具体的な代償に弱い [U8][U9][U10]。
- **National Issues Forums（イシューガイド）**: 3 案＋各案の代償。6〜12 人、各案に等時間、「うまくいったら代償は？」と問う [U11][U12]。

### 対面
- **討論型世論調査**: 2012 年エネルギーは 6,849 人 → 285 人、ゼロ案支持 32.6 → 46.7%。藤沢市 2010 は 3,000 通 → 1,217 回答 → 258 人、15〜20 人班・合意不要・疑問は専門家へ [U13][U14][U15]。
- **気候市民会議**: 札幌 2020 は 3,000 通 → 応募 48（1.6%）→ 20 人、各班に 2 名のファシリ。札幌 2025 は 39 人、379 案 → 84 提案＋11 プロジェクト。武蔵野 2022 は 68 人。国内 28 市区町、つくば市長は 74 項目すべて対応を約束 [U16][U17][U18][U19]。
- **三鷹市**（総務省 2009）: 1,000 通 → 60 人抽選。98% が初参加、95% が継続希望。課題 = 情報提供の質、「結論ありき」、無償ボランティア依存 [U23]。

### お金・担い手
- Balancing Act（2024）: 収支均衡が必須、初期値で結果が動く [U24]。厚木市 市民協働提案事業（2023）: 総額 650 万円（市負担 200 万円）で気候市民会議 [U25]。鎌倉の相互提案協働事業は年 1〜5 件（2014〜18）[U26]。co-production の証拠は弱く、短期の委託・階層組織が失敗要因 [U27]。Habermas Machine（2024）: AI の合意文案が人間案より 56 対 44 で選好、代表性が前提 [U28]。

## 設計原則（応用機能の段階で使う）

1. 要望でなく「選択肢＋代償」で出させる（NIF）。
2. 収支の枠を先に見せ、超えたら進めない。初期値は中立に。費用は桁で出し、確認は行政側へ。
3. 事実・体験・要望を別欄に。事実は出典必須。
4. 賛否は人でなく理由で並べ、他人の理由を取り込める形に。二分木は折衷を置けない。
5. 反対は拒否権でなく「困る人あり」の申告にして修正義務へ。
6. 4〜20 人・ファシリつき・締切つきのラウンド。班替えで偏りと支配的な発言を防ぐ。
7. 無作為抽出を混ぜる。参加希望は 1.6〜7.3% なので多めに招待し、年代・地区で抽選。公募のみは動員と偏り。
8. 市が決められる範囲と出口（受け手・期限・返答）を先に約束し、対応状況を公開。
9. 「誰がやるか」を成果物に組み込む（鎌倉の 3 層、厚木）。
10. AI は束ね役。結論と代表性の判断は人。

## 段階表（設計案）

| 段階 | 必要な情報 | オンライン | 対面（リビング） |
|---|---|---|---|
| 困りごと | 誰がどこで困るか、既存の制度 | 短文の投稿、AI で束ねる（原文リンク・小さな束も表示） | 聞き取り、声なき声の招待 |
| 案を出す | 案の型（行政／事業者／市民）、費用の桁、仮の担い手、困る人 | 案カード（必須欄）、似た案の統合 | 課題 → 案の 2 コマ式（三鷹） |
| 比べる | 3 案前後の代償、収支の枠、財源の候補 | 理由の並べ替え、予算ゲーム | 4〜8 人卓で等時間、職員への質問を集約 |
| 磨く | 反対理由への修正、費用の再見積り、担い手の名乗り、困る人の同意 | 期限つきの立場表明、修正版 | 当事者を交えた修正会、現地確認 |
| 届ける／自分でやる | 提出先・期限・返答／担い手名簿・初年度費用・財源・試行期間 | 提案書の自動整形、進捗公開 | 行政との対話、キックオフ |

## 鎌倉での運用案（推測を含む）

- 人口 17 万は三鷹（175,009）に近い。基準線は「約 2,500 通 → 46 人、全 4 回、市長へ手交」。体制の前例は「主催 = 実行委員会、協力 = 市、事務局 = 外部法人」。
- 年 1 回は市の協力で住基抽出の会議（抽出は NIHO 単独では不可）、平常は会員＋地域団体からの層化公募と抽選。リビングで 4〜6 人卓、1 テーマ 20〜50 人、2〜3 時間 × 2 回。
- オンラインは案ごとに 2 週 × 3 の締切つき、同時進行は月 3 案まで。
- 出口 = 相互提案協働事業、提案公募型委託、環境基本計画の見直し。自分たちでやるなら厚木型の協働提案。費用は厚木の総額 650 万円が目安、無償ボランティア依存は避ける。

## 未確認

- 2012 年 DP の政策反映、川崎・所沢の計画反映の原本、鎌倉の会議後アンケートと市の具体的な反映、有効性感覚の数値、厚木以外の運営費、OECD 原則の本文。Loomio・Kialo・NIF の独立評価。鎌倉の相互提案要綱の原本。

## 出典（抜粋）

- [U1] https://homes.cs.washington.edu/~borning/papers/kriplean-cscw2012.pdf ／ [U2] https://www.opendemocracy.net/en/loomio-and-problem-of-deliberation/ ／ [U3] https://www.loomio.com/about ／ [U4] https://en.wikipedia.org/wiki/Kialo ／ [U5] https://citizens.is/blog/citizens-foundation-main-projects/ ／ [U6] https://citizens.is/impact/my-neighbourhood/ ／ [U7] https://istc.cnr.it/en/node/73919
- [U8] https://scrapbox.io/nishio/デジタル政策フォーラム講演2025-11-19 ／ [U9] https://www.seisakukikaku.metro.tokyo.lg.jp/documents/d/seisakukikaku/kangaekata3 ／ [U10] https://scrapbox.io/nishio/シン東京2050ブロードリスニング ／ [U11] https://politicalsciencenow.com/deliberate-forums-issue-guide-review/ ／ [U12] https://nifi.org/wp-content/uploads/2025/02/Climate-Choices-Moderators-Guide.pdf
- [U13] https://en.wikipedia.org/wiki/Deliberative_opinion_poll ／ [U14] https://keiodp.sfc.keio.ac.jp/wp-content/uploads/DP検証会合資料1.pdf ／ [U15] https://keiodp.sfc.keio.ac.jp/wp-content/uploads/fujisawa1/6-report.pdf ／ [U16] https://eprints.lib.hokudai.ac.jp/repo/huscap/all/80247/sapporo2020ca_report_210119.pdf ／ [U17] https://city.sapporo.jp/kankyo/ondanka/climate_citizens_assembly/documents/250327_ikenteiansyo.pdf ／ [U18] https://www.city.musashino.lg.jp/_res/projects/default_project/_page_/001/044/219/HP/7-3.pdf ／ [U19] https://www.city.gifu.lg.jp/_res/projects/default_project/_page_/001/034/784/kokuen02.pdf
- [U20] https://www.pref.kanagawa.jp/documents/113723/kamakura_oriennteteshonn_.pdf ／ [U21] https://www.pref.kanagawa.jp/docs/ap4/prs/r7453769.html ／ [U22] https://www.city.kamakura.kanagawa.jp/kisya/data/2025/documents/20250304.pdf ／ [U23] https://www.soumu.go.jp/iken/pdf/090313_5_2.pdf
- [U24] https://www.cambridge.org/core/services/aop-cambridge-core/content/view/BCB8FB02A6E42EA19F695A16C28DC44C/S2398063X24000381a.pdf/more-than-a-wink-and-a-nudge-examining-the-choice-architecture-of-online-government-budget-simulations.pdf ／ [U25] https://www.city.atsugi.kanagawa.jp/material/files/group/3/202305220003.pdf ／ [U26] https://www.city.kamakura.kanagawa.jp/keiki/hyouka/documents/r01shimin02.pdf ／ [U27] https://www.govint.org/our-resources/publications/publication/user-and-community-co-production-of-public-services-what-does-the-evidence-tell-us ／ [U28] https://www.rivista.ai/wp-content/uploads/2024/10/science.adq2852.pdf ／ [U29] https://commonslibrary.org/facilitation-skills-for-deliberative-democracy/
