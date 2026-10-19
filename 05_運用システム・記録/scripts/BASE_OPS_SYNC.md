# BASE → LIMB運営表（切替準備）

対象は native Google Sheet `1bB-pnCvqC9svrwZgquCFHMqW0vJqMypM2w3pEaxcTl0` の8タブです。旧5シート台帳の `base_ledger_sync.py` は現状維持です。正本の決定、認証設定、実データ照合が済むまで新writerを有効化しません。

## 取得と更新範囲

- BASE API v2 の PAT（`items.read` / `orders.read`）で商品一覧、注文検索、注文詳細を読みます。BASEへの書込APIは呼びません。
- `商品・在庫マスター` の固定BASE商品ID 74:87、種類キー 142:169 に一致する行だけ更新します。未取得は前回数値を保持し、種類別K列・商品別N列・見える種類別I列に前回値と表示します。API値0は数値0として書きます。取得日J列、冒頭A2、ダッシュボードD7は成功時だけ更新し、一部未取得なら前回値が含まれる旨を明記します。未対応IDや行不足は全体を中止します。
- `受注・売上・利益` の注文ID 5:104、注文ID＋明細ID 5:104 で照合します。注文の状態・売上（送料込）・BASE手数料・発送日時/件数と注文明細を更新します。日時B/Oは日本時間のExcel/Sheets数値日時です。IDが空でもR:Xなどに手入力が残る行は新規割当しません。実送料R、返金・調整S、経費T、原価U、再投資V、返金確認W、精算確認Xは書き換えません。既存Y/AB式にはQ列の取得状態ガードを付け、検索で未取得なら利益を確定にせず集計対象から外します。既存式が想定外なら全体を中止します。返品/部分返金は別APIで確認できないため、確定利益は手入力の確認が揃うまで未確定です。
- 購入者氏名・メール・住所・電話、注文メモ、追跡番号、API生レスポンス、認証値は保存・出力しません。

## 使い方と切替順

Python環境には既存台帳と同じ `openpyxl` が必要です。初回は `BASE_PAT` をプロセス環境変数に設定し、native表を変更せず正規化件数を確認します。

```powershell
python 05_運用システム・記録/scripts/base_ops_sync.py --from-date 2026-10-01 --to-date 2026-10-18
```

native表を正本と決めた後、短命のGoogle Sheets OAuthアクセストークンを `GOOGLE_SHEETS_ACCESS_TOKEN` に設定するか、サービスアカウントJSONを `GOOGLE_SERVICE_ACCOUNT_JSON` に設定します。後者では実行時に短命トークンを取得します。対象Sheetへの編集権限が必要です。まず `--sheet-id 1bB-pnCvqC9svrwZgquCFHMqW0vJqMypM2w3pEaxcTl0` のみで計画件数を確認し、BASE側商品/種類IDと既存14商品・28種類、注文/明細の行対応を照合します。初回実行前にnative SheetとExcelの現行版を別名保存してください。

```powershell
python 05_運用システム・記録/scripts/base_ops_sync.py --from-date 2026-10-01 --to-date 2026-10-18 --sheet-id 1bB-pnCvqC9svrwZgquCFHMqW0vJqMypM2w3pEaxcTl0
```

一致が確認できたら同じ指定に `--apply` を加えます。書込直前に対象範囲と計算式を再読取し、計画時から変わっていれば中止します。取得値・式の鮮度ガード・取得日時表示・`ダッシュボード!H20:I21` の最終成功記録は1回のSheets batchUpdateへまとめます。API/計画失敗時は一切書き込まず、数値セルを0で上書きせず、非0終了します。Google Sheets APIに原子的な編集競合ロックはないため、実行中の同じセルの手編集は避け、成功後に主要指標を照合してください。

新表の注文総額・利益未確定状態・在庫点数/金額、ID件数、手入力列の保存を確認してから、旧5シートの手動運用を停止します。切替前に不一致が出た場合は新writerを実行せず、旧台帳で継続します。切替後の問題は新writerを停止して保存したnative/Excelの版へ戻し、旧writerの再開は重複計上を照合してから行います。

## 無人実行の準備（未有効）

候補時刻は毎日 **08:30 JST = 前日23:30 UTC** です。`.github/workflows/base-ops-sync.yml` は現在 `workflow_dispatch` のみで、cronはコメントのままです。Google Sheet正本の確認後、GitHub Secrets `BASE_PAT` と `GOOGLE_SERVICE_ACCOUNT_JSON` を設定し、対象Sheetをサービスアカウントのメールアドレスへ編集共有します。サービスアカウントJSONはログやファイルに保存せず、実行時にSheets用の短命トークンへ交換します。依存は `05_運用システム・記録/scripts/requirements-base-ops.txt` に固定しました。現時点ではスケジュール・Secret・外部権限を設定していません。PCがオフでもGitHub Actionsは実行できますが、GitHub側のスケジュール開始時刻には遅延があり得ます。

実行結果はGitHub Actionsのジョブ結果とRun summaryに件数・成否だけ記録します。ユーザー側でActions通知を有効にすれば失敗通知を受けられます。**09:00ちょうどの配信はGitHub通知だけでは保証できません**。時刻指定の報告が必要なら別の通知先と送信権限を確認してから追加します。

必要な情報: ①正本をGoogle native/Excelのどちらにするか、②BASE PAT（`items.read`,`orders.read`）をユーザー側のSecretへ設定すること、③Google native正本ならサービスアカウントJSONのSecretとSheet共有、④注文検索の初期取得開始日と毎回の再取得期間。PATやGoogle認証値をチャットやファイルへ貼らないでください。

検証: `python -m unittest scripts.tests.test_base_ops_sync -v` は合成レスポンスのみを使います。BASE実データ取得とGoogle Sheet書込は認証・正本未確定のため未実施です。

API仕様: [商品一覧](https://apiv2.thebase.com/docs/endpoints/get-api-items/) / [注文検索](https://apiv2.thebase.com/docs/endpoints/post-api-orders-search/) / [注文詳細](https://apiv2.thebase.com/docs/endpoints/get-api-orders-unique-key/)。
