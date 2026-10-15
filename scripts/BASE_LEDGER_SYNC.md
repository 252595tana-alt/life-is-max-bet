# BASE 読み取り台帳更新

BASE API v2 の `items.read` と `orders.read` を付けた Personal Access Token（PAT）で、既存 Excel 台帳のコピーを更新します。Python 3 と `openpyxl` が必要です（`python -m pip install openpyxl`）。BASE への更新 API は呼びません。

PowerShell 例（PAT は入力後のセッション内だけに保持し、ファイルへ保存しない）:

```powershell
$env:BASE_PAT = [System.Net.NetworkCredential]::new('', (Read-Host 'BASE PAT' -AsSecureString)).Password
python scripts/base_ledger_sync.py --workbook 'outputs/inventory-20261014/販売戦略_Life_is_Max_Bet_v3.2_確定金額・EC在庫連携.xlsx' --output 'outputs/base-ledger-current.xlsx' --from-date 2026-10-01 --to-date 2026-10-15
Remove-Item Env:BASE_PAT
```

`--from-date` と `--to-date` は注文日（JST）の両端を含み、最大 1 年です。注文全件が必要なら、販売開始日から期間を分けて実行してください。期間ごとの注文はこの版では累積せず、指定期間の結果に置き換わります。再実行時は同じ出力ファイルを `--workbook` に指定してもよく、同期シートを置き換えて重複を避けます。元ファイルを残す運用を推奨します。

③-3 の BASE ID がある行の名称・税込価格、③-4 の同 ID 行の名称・商品合計在庫だけを更新します。原価、粗利の数式、計画商品行は保ちます。台帳にない商品と全種類の在庫は `BASE商品・種類` に記録します。注文の期間内概要と明細は `BASE注文`、`BASE注文明細` に記録します。購入者氏名、連絡先、住所、注文メモ、追跡番号、API の生データは保存しません。

`BASE取得状態` に商品・注文の完了、期間内注文 0 件、台帳商品の未取得件数を分けて記録します。0 在庫は API が明示した場合のみ書き込みます。API エラー、欠けた必須項目、ページ不整合では出力ファイルを置き換えません。既存行の ID が API 一覧に無い場合は古い値を保持するため、`BASE取得状態` を確認してください。

注文合計、BASE 徴収手数料、顧客負担の送料は API の値です。実際の配送費、製造原価、返金、振込額はこの API 読み取りだけでは確定しません。利益や販売者報酬を確定値として算出しません。`③-4` の合計等の Excel 数式は通常の Excel で開いた時に再計算されます。

API 仕様: [商品一覧](https://apiv2.thebase.com/docs/endpoints/get-api-items/) / [注文検索](https://apiv2.thebase.com/docs/endpoints/post-api-orders-search/) / [注文取得](https://apiv2.thebase.com/docs/endpoints/get-api-orders-unique-key/)。API はベータ版のため仕様変更時は同期を止めて照合してください。
