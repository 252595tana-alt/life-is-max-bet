# SEO実施記録（Phase 1–7）

更新日: 2026-10-20。GSC・GA4・BASE管理画面・URL検査・Lighthouseの値は、同日に共有された確認結果を記録した。未取得の数値は推定しない。BASEショップと別ドメインのブランドTOPを混同しない。

## 対象と現状

- BASEショップ: `https://lifeismaxbet.base.shop/`。GSC URL-prefixプロパティを新規登録し、GA4で所有権を自動確認した。`sitemap.xml` は送信成功、検出20ページ。
- GSC URL検査: BASE TOPはGoogle登録済み。`https://lifeismaxbet.base.shop/items/162021466` と `https://lifeismaxbet.base.shop/items/162021520` は「URLがGoogleに認識されていない」。登録リクエストは未実施。
- ブランドTOP公開先設定: `https://polished-river-d244.252595tana.workers.dev/`（`04_サイト公開/commerce.config.json`）。今回のサイト変更はローカル実装・ビルド済みで、公開反映は未確認。
- GitHub Pagesはデザインプレビュー。previewビルドは `noindex` と `robots.txt` の `Disallow: /`、productionビルドは `robots.txt` の `Allow: /` とcanonical・OG URLを生成した。
- `commerce.config.json` は `enabled: false`。productionのSEO公開と購買リンクの有効化は分離した。確認済みの商品マッピングはなく、生成TOPの商品カード9件はリンクを外し、BASEショップTOPへの一般導線を残した。
- BASEのSEO App、HTMLタグ App、Blog Appは導入済み。SEO Appで設定済みなのはTOP・ABOUT・RED EYEの2商品。公開11商品のうち9商品のSEO欄が空欄。ブログ投稿は0件。
- BASE TOPのcanonical、robots、sitemapは正常。商品ページにProduct JSON-LDがある。商品画像のaltは実質未設定。Merchant Centerの現アカウントはない。

## KPI基準値

| 指標 | 対象・定義 | 基準期間 | 基準値 | 取得日 | 出典・状態 |
| --- | --- | --- | --- | --- | --- |
| 検索クリック | GSC、BASE URL-prefix | 初期値 | 0 | 2026-10-20 | GSC。処理中のため期間比較は未実施 |
| 検索表示回数・CTR・平均順位 | GSC、BASE URL-prefix | 初期値 | 未取得 | 2026-10-20 | GSC処理中 |
| サイトマップ検出ページ | GSC、BASE `sitemap.xml` | 送信時 | 20 | 2026-10-20 | 送信成功。インデックス登録数とは区別 |
| 総セッション | GA4 `LIFE IS MAX BET｜BASE`（558523334） | 2026-09-22〜10-19 | 55 | 2026-10-20 | 測定ID `G-LPC0Q7ERQK` |
| チャネル別セッション | 同GA4、Direct / Referral / Unassigned | 同上 | 42 / 10 / 3 | 2026-10-20 | Organic Search行なし |
| 自然検索セッション | 同GA4、Organic Search | 同上 | 0（行なし） | 2026-10-20 | 現時点の画面表示。ブランドTOPの値ではない |
| アクティブユーザー・ページ表示 | 同GA4 | 同上 | 15人 / 210回 | 2026-10-20 | GA4表示 |
| BASE TOPページ表示 | 同GA4、`/` | 同上 | 94回 | 2026-10-20 | GA4表示 |
| 主要商品ページ表示 | 同GA4、`/items/{ID}` | 同上 | 下表参照 | 2026-10-20 | GA4表示 |
| キーイベント・eコマース購入・収益 | 同GA4 | 同上 | 0 / 0件 / ¥0 | 2026-10-20 | GA4表示。BASE管理画面の売上とは別指標 |
| ブランドTOP→BASE遷移 | ブランドTOPの一般ショップリンク | 未設定 | 未取得 | 未取得 | 計測定義・実装を要確認 |
| ブランドTOPの検索実績 | ブランドTOPのGSC・GA4 | 未設定 | 未取得 | 未取得 | BASEプロパティの値を流用しない |

GA4の商品ページ表示（同じ過去28日）:

| BASE商品ID | ページ表示 |
| --- | ---: |
| 162393479 | 13 |
| 162396602 | 10 |
| 162393382 | 9 |
| 162393404 | 9 |
| 162393312 | 8 |
| 162393547 | 8 |
| 162393799 | 8 |
| 162393743 | 7 |

## Phase 1｜現状・計測

- 確認日: 2026-10-20。GSC・GA4の基準値は上表。BASEの自然検索流入はGA4の表示上0、GSCのクリック初期値0。GSCの表示回数・CTR・順位は処理中で未取得。
- 次回確認: GSC処理完了後、同じURL-prefixと期間でクリック・表示・CTR・順位を再取得する。

## Phase 2｜技術状態

- BASE TOPのcanonical・robots・sitemapは正常、商品ページにProduct JSON-LDあり。商品画像のaltは実質未設定。
- Lighthouse mobile: Performance 37、SEO 92、FCP 3.8秒、LCP 8.5秒、CLS 0、TBT 3970ms。測定URLと実行条件の保存は未確認のため、改善前後の厳密比較には再測定が必要。
- GSC URL検査ではBASE TOP登録済み、商品 `162021466` と `162021520` は未認識。インデックス登録リクエストは未実施。

## Phase 3｜検索語候補

検索量と順位は未取得。優先度はブランドとの適合と検索意図による仮説であり、実測値ではない。「アカメ」と商品の対応は実資料で未確認。

| 候補 | 想定する検索意図 | 適合・優先度 | 確認事項 |
| --- | --- | --- | --- |
| LIFE IS MAX BET | ブランドを探す | 高 | 表記・TOP導線を統一 |
| ライフイズマックスベット | ブランドを日本語で探す | 高 | 実際の表記揺れを確認 |
| 釣り ストリート アパレル | テイストに合うブランドを探す | 高 | ブランド説明との整合 |
| フィッシング ストリートブランド | ブランド比較・探索 | 高 | 自社表現との整合 |
| アカメ Tシャツ | 特定モチーフの商品探索 | 要確認 | アカメと既存商品の対応を実資料で確認 |
| 釣り グラフィック Tシャツ | 商品比較・探索 | 中 | 該当商品と図柄の確認 |
| 釣り スウェット | 商品比較・探索 | 中 | 該当商品・季節性の確認 |
| 釣り ファッション | 着こなし・情報探索 | 中 | ブログ内容との整合 |

## Phase 4｜比較調査

- 競合例としてAparache、Fish Hook IRIE等を確認。ブランド説明、コンテンツ、カテゴリへの導線が明確だった。
- 自社への適用候補は説明と導線の整理。競合の検索流入、順位、売上の差は未取得で、効果を断定しない。

## Phase 5｜ページとコンテンツ

- BASE SEO AppでTOP・ABOUT・RED EYEの2商品を設定済み。公開11商品のうち残る9商品はSEO欄が空欄。各商品の実情報に基づく入力と保存は未実施。
- Blog Appは導入済み、投稿0件。下書きは `SEOブログ下書き_ブランドコンセプト.md` と `SEOブログ下書き_釣りとストリート.md`。投稿・公開は未実施。
- BASEの商品画像altは実質未設定。画像内容とBASE側の編集可否を確認してから対応する。

## Phase 6｜ブランドTOPのローカル変更

- `04_サイト公開/index.html` にOG site name・localeを加え、BASEへの一般導線のリンク文言を明確化。`styles.css` はリンク無効時の誤解を招くホバー装飾を抑えた。
- `05_運用システム・記録/scripts/build-site.mjs` でSEOのindexable判定を購買の `enabled` から分離。productionはcanonical・OG URL・robots Allow、previewはnoindex・robots Disallow。未確認の商品カードは非リンクで出力する。
- production／previewビルドと生成結果のアサーションは成功。commit・push・実サイトへの反映はレビュー・QA後の作業で、現時点では未実施。

## Phase 7｜公開後の確認と改善

- UI確認待ち: BASE SEO Appの未設定9商品の保存、ブログ2稿の投稿、未認識商品のGSC登録リクエスト。実施したものとして記録しない。
- 公開後はブランドTOPの実URLでcanonical・robots・OG・一般ショップ導線を確認し、GSCのBASE値と別にブランドTOPの検索実績を記録する。
- Merchant Centerは現アカウントなし。作成・連携は未実施。

## 変更履歴

| 日付 | Phase | 変更・調査 | 対象ファイル・URL | 検証・出典 | 公開状態 |
| --- | --- | --- | --- | --- | --- |
| 2026-10-20 | 1–5 | GSC・GA4・BASE・Lighthouseの初期値と未確認項目を記録 | BASE URL-prefix | 同日のUI確認結果として共有 | 記録のみ |
| 2026-10-20 | 5 | ブログ2稿をMarkdownに下書き | `05_運用システム・記録/SEOブログ下書き_*.md` | 既存ブランド文言と商品URLに照合 | 未投稿 |
| 2026-10-20 | 6 | SEO公開と購買リンクの判定を分離 | `04_サイト公開/`、`build-site.mjs` | production／previewビルドと生成HTML検査 | ローカル実装、公開未確認 |
