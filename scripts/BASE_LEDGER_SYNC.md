# BASE 読み取り台帳更新

台帳は `DROP計画／商品・在庫／売上・利益／報酬分配／ダッシュボード` の5シートです。Python 3 と `openpyxl` が必要です（`python -m pip install openpyxl`）。BASE API v2 の PAT には `items.read` と `orders.read` だけを付けます。BASE への更新 API は呼びません。

旧台帳を5シートへ移す場合は、元ファイルを別名で保存してから、PATを使わずに次を実行します。現在の `【販売戦略】/販売計画/base-ledger-current.xlsx` は移行済みです。

```powershell
python scripts/base_ledger_sync.py --migrate-only --workbook '【販売戦略】/販売計画/base-ledger-current.xlsx' --output '【販売戦略】/販売計画/base-ledger-current.xlsx'
```

次回の同期は5シート台帳を入力・出力の両方に指定します。PATは画面に表示せず、ファイルに保存しません。

```powershell
$env:BASE_PAT = [System.Net.NetworkCredential]::new('', (Read-Host 'BASE PAT' -AsSecureString)).Password
python scripts/base_ledger_sync.py --workbook '【販売戦略】/販売計画/base-ledger-current.xlsx' --output '【販売戦略】/販売計画/base-ledger-current.xlsx' --from-date 2026-10-01 --to-date 2026-10-15
Remove-Item Env:BASE_PAT
```

`--from-date` と `--to-date` は注文日（JST）の両端を含み、1回の検索期間は最大1年です。取得済み注文は注文キーで統合し、明細は注文キーと明細IDで統合します。再実行しても同じ注文を二重計上しません。期間外の取得済み注文は残ります。期間内で再検索時に見つからない注文は前回値として残し、利益計算を保留します。API失敗や必須項目不備では台帳を置き換えません。

`商品・在庫` の上部は計画商品とBASE実商品の単価・原価表です。55〜65行に商品合計在庫、72行以降に商品・種類IDと種類別在庫を置きます。既存商品IDでのみ単価・在庫を更新します。API一覧に無い台帳商品は古い値を保持し、`ダッシュボード` の取得状態に未取得件数を出します。APIが返した在庫0と未取得は区別します。台帳未登録の商品も種類別一覧へ残します。

`売上・利益` のA:T列は注文、V:AF列は明細です。N:Q列に実送料、返金・調整、その他実費、商品原価実績を手入力します。実績0も空欄にせず `0` と入力します。R列を `確定` にすると、発送履歴があり発送済みの注文について、S列に梱包報酬控除前の利益が計算されます。原価や実送料、返金状況などが未確認の間は利益を空欄に保ちます。APIの顧客送料と実際の配送費は別の値です。

`報酬分配` のB列は発送実績件数を表示します。梱包担当名はC列に手入力します。利益が確定した注文だけ、発送履歴ID1件につき梱包担当報酬150円をD列に計算します。確定利益から梱包報酬を控除した額が正なら森本50%・田中50%、赤字なら分配0として赤字額を別記します。未確定の注文は報酬額と分配額を空欄に保ちます。報酬ルールは同シートのL:M列に表示します。

`DROP計画` は商品×デザイン別の1行で、F:Q列が3月〜2月、R列が年間数量です。空欄は予定なし、`予定` は販売予定だが数量未入力、`要入力` は数量未確定、数値の `0` は実際の数量0を示します。35〜42行に月別・年間の集計、47〜49行にステッカーの月別販売単価、54〜58行に月別経費を置きます。月別単価・経費の黄色いセルを入力できます。売上・粗利は入力済み分の集計（未確定分を除く）と未確定件数を併記します。単価が空欄なら `0` と扱わず未確定にします。計算内訳は153行の左にある `＋` で展開できます。ロンT・Tシャツ・キャップ①のオリロゴと新作は別行です。Tシャツ2月の12点は `共通` に置き、デザイン別に推測配分していません。

購入者氏名、メール、住所、電話、注文メモ、追跡番号、APIの生データは保存しません。Excelの数式は通常Excelで開いた時に再計算されます。APIはベータ版のため仕様変更時は同期を止めて照合してください。

API仕様: [商品一覧](https://apiv2.thebase.com/docs/endpoints/get-api-items/) / [注文検索](https://apiv2.thebase.com/docs/endpoints/post-api-orders-search/) / [注文取得](https://apiv2.thebase.com/docs/endpoints/get-api-orders-unique-key/)。
