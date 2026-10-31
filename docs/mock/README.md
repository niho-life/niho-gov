# モック

自己完結の HTML（外部依存なし）。画面には UI と URL だけを置き、論点・見本の範囲・作っていない部分は各ファイル冒頭の HTML コメントに書く。

| 版 | ファイル | 公開 | 内容 |
|---|---|---|---|
| v1 | `gikai-v1.html` | https://niho-gikai-mock.pages.dev/v1 | 段階 1「わかる」: ホーム・9月定例会（5 トピック）・テーマの経緯（市役所の移転・学校の暑さ対策）・予算（ツリーマップ→款→事業、ひとりあたり・ひと月、去年から、お金はどこから）・議員・聞く。スマホ／PC の切替つき。ひとこと（賛否＋100 字）も載せている || v2 | `gikai-v2.html`（画像は `assets/`） | https://niho-gikai-mock.pages.dev/ （トップ。owner 指示で 2026-10-31 夜に公開。v1 は /v1）。`gikai-v2-single.html` は画像を埋め込んだ 1 ファイル版（生成物なので git には置かない） | 拡充版: 写真つきホーム「鎌倉のいま」（動いていること・次に起きること・テーマ・街のこれから・自分にできること）・テーマの写真カード一覧→詳細（スタンプは賛否型／同意型〔ソシオクラシー〕の切替・論点・経緯・意見の整理・資料室・提案）・資料室（種類別／年表）・フォーラム（GitHub Discussions 型の投稿とコメント。市・議員・事業者も同じ形で参加。案の比較などは応用機能として未実装）・街の目標（進み具合）・予算（コインのインフォグラフィック追加）。v1 の議会・予算・議員・聞くも含む |

公開は `publish-cf ~/Documents/app/NIHO/niho-gikai-mock-publish niho-gikai-mock`（Cloudflare Pages。`_headers` で noindex と connect-src 'none'）。公開ステージの `index.html` がトップ。

画像の出典は `assets/CREDITS.md`。仮画像なので本番では差し替える。ローカル確認は niho-app の `.claude/launch.json` の `gikai-mock`（`python3 -m http.server 8795 --directory docs/mock`）。
