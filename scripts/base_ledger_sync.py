"""Read BASE API v2 data into a copy of the existing Excel ledger.

Only the item list, order search and order detail endpoints are called. No raw
API response is persisted because it contains buyer personal information.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import json

from openpyxl import load_workbook


API_ORIGIN = "https://apiv2.thebase.com"
SHEET_PRICES = "③-3 商品単価・原価"
SHEET_STOCK = "③-4 EC在庫"
SHEET_ITEMS = "BASE商品・種類"
SHEET_ORDERS = "BASE注文"
SHEET_LINES = "BASE注文明細"
SHEET_RUN = "BASE取得状態"


class SyncError(Exception):
    pass


def valid_order_range(start: date, end: date):
    try:
        next_year = start.replace(year=start.year + 1)
    except ValueError:  # February 29
        next_year = date(start.year + 1, 3, 1)
    return start <= end < next_year


def excel_text(value):
    """Keep API supplied names as literal text, never spreadsheet formulas."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def required_int(obj, key, label):
    value = obj.get(key)
    if type(value) is not int or value < 0:
        raise SyncError(f"{label}.{key} が未取得または不正")
    return value


def required_list(obj, key, label):
    value = obj.get(key)
    if not isinstance(value, list):
        raise SyncError(f"{label}.{key} が未取得または不正")
    return value


def require_fields(obj, keys, label):
    if not isinstance(obj, dict) or any(key not in obj for key in keys):
        raise SyncError(f"{label} に必要な項目がありません")


class BaseClient:
    def __init__(self, token: str):
        if not token:
            raise SyncError("BASE_PAT 環境変数がありません")
        self.token = token

    def request(self, method: str, path: str, payload=None):
        if method not in ("GET", "POST") or not path.startswith("/api/"):
            raise SyncError("許可されない API 操作")
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            API_ORIGIN + path,
            data=body,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/json",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            raise SyncError(f"BASE API HTTP {exc.code}: {method} {path.split('?')[0]}") from None
        except (URLError, TimeoutError, ValueError) as exc:
            raise SyncError(f"BASE API 取得失敗: {method} {path.split('?')[0]}") from None

    def items(self):
        found = {}
        offset = 0
        while True:
            page = self.request("GET", "/api/items?" + urlencode({"limit": 100, "offset": offset}))
            if not isinstance(page, list):
                raise SyncError("商品一覧の形式が不正")
            for item in page:
                require_fields(item, ("id", "name", "stock", "price", "variations"), "商品")
                item_id = required_int(item, "id", "商品")
                if item_id in found:
                    raise SyncError(f"商品 ID {item_id} が複数ページに重複")
                stock = required_int(item, "stock", "商品")
                variations = required_list(item, "variations", "商品")
                if variations:
                    variation_ids = set()
                    for variation in variations:
                        require_fields(variation, ("id", "stock"), "種類")
                        variation_id = required_int(variation, "id", "種類")
                        if variation_id in variation_ids:
                            raise SyncError(f"商品 ID {item_id} の種類 ID が重複")
                        variation_ids.add(variation_id)
                        required_int(variation, "stock", "種類")
                    if sum(v["stock"] for v in variations) != stock:
                        raise SyncError(f"商品 ID {item_id} の種類別在庫と合計が不一致")
                price = item["price"]
                if price is not None:
                    required_int(item, "price", "商品")
                found[item_id] = item
            if len(page) < 100:
                return found
            offset += len(page)
            if offset > 1_000_000:
                raise SyncError("商品一覧が API のページング上限を超えました")

    def orders(self, start: date, end: date):
        if not valid_order_range(start, end):
            raise SyncError("注文期間は開始日から 1 年未満にしてください")
        summaries = {}
        page_number = 1
        while True:
            payload = {
                "ordered_from_date": start.isoformat(),
                "ordered_to_date": end.isoformat(),
                "sort": "ordered_asc",
                "limit": 200,
                "page": page_number,
            }
            page = self.request("POST", "/api/orders/search", payload)
            require_fields(page, ("orders", "pagination"), "注文検索")
            pagination = page["pagination"]
            require_fields(pagination, ("page", "total_pages", "total_count", "has_next"), "注文ページング")
            if pagination["page"] != page_number or type(pagination["has_next"]) is not bool:
                raise SyncError("注文ページングが不整合")
            for summary in required_list(page, "orders", "注文検索"):
                require_fields(summary, ("unique_key",), "注文概要")
                key = summary["unique_key"]
                if not isinstance(key, str) or not key.isalnum() or len(key) != 16:
                    raise SyncError("注文キーが不正")
                summaries[key] = summary
            if not pagination["has_next"]:
                if page_number != pagination["total_pages"] and pagination["total_pages"] != 0:
                    raise SyncError("注文ページ数が不整合")
                if len(summaries) != required_int(pagination, "total_count", "注文ページング"):
                    raise SyncError("注文件数が API の総件数と不一致。期間を分割して再取得してください")
                break
            if page_number >= 500:
                raise SyncError("注文検索が 500 ページ上限に到達。期間を分割してください")
            page_number += 1
        details = {}
        for key in summaries:
            detail = self.request("GET", "/api/orders/" + quote(key))
            require_fields(detail, ("unique_key", "status", "ordered_at", "amounts", "lines", "delivery"), "注文詳細")
            if detail["unique_key"] != key:
                raise SyncError("注文詳細と検索結果のキーが不一致")
            normalize_order(detail)  # Fail before touching the workbook.
            details[key] = detail
        return details


def normalize_order(order):
    amounts = order["amounts"]
    delivery = order["delivery"]
    require_fields(amounts, ("subtotal", "shipping_fee", "cod_fee", "total", "service_charge", "additional_charges"), "注文金額")
    require_fields(delivery, ("dispatched_at", "dispatches"), "配送")
    require_fields(amounts["service_charge"], ("collected_fee",), "BASE手数料")
    line_rows = []
    line_ids = set()
    for line in required_list(order, "lines", "注文詳細"):
        require_fields(line, ("id", "item_id", "variation_id", "title", "price", "amount", "total", "status", "shipping_fee"), "注文明細")
        line_id = required_int(line, "id", "注文明細")
        if line_id in line_ids:
            raise SyncError("同一注文内の明細 ID が重複")
        line_ids.add(line_id)
        for field in ("item_id", "price", "amount", "total", "shipping_fee"):
            required_int(line, field, "注文明細")
        if line["variation_id"] is not None:
            required_int(line, "variation_id", "注文明細")
        line_rows.append((order["unique_key"], line_id, line["item_id"], line["variation_id"], excel_text(line["title"]), excel_text(line.get("variation")), line["price"], line["amount"], line["total"], line["status"], line["shipping_fee"]))
    dispatch_ids = set()
    dispatch_rows = []
    for dispatch in required_list(delivery, "dispatches", "配送"):
        require_fields(dispatch, ("id", "dispatched_at", "order_line_ids"), "発送履歴")
        dispatch_id = required_int(dispatch, "id", "発送履歴")
        if dispatch_id in dispatch_ids:
            raise SyncError("同一注文内の発送 ID が重複")
        dispatch_ids.add(dispatch_id)
        dispatch_rows.append(f"{dispatch_id}:{dispatch['dispatched_at']}:{','.join(map(str, dispatch['order_line_ids']))}")
    additional = required_list(amounts, "additional_charges", "注文金額")
    additional_values = []
    for charge in additional:
        require_fields(charge, ("name", "collected_fee"), "追加料金")
        additional_values.append(f"{charge['name'] or ''}:{charge['collected_fee'] if charge['collected_fee'] is not None else '未取得'}")
    order_row = (
        order["unique_key"], order["ordered_at"], order["status"],
        required_int(amounts, "subtotal", "注文金額"), required_int(amounts, "shipping_fee", "注文金額"),
        required_int(amounts, "cod_fee", "注文金額"), required_int(amounts, "total", "注文金額"),
        required_int(amounts["service_charge"], "collected_fee", "BASE手数料"),
        excel_text("; ".join(additional_values)), delivery["dispatched_at"], "; ".join(dispatch_rows),
        "原価・実送料未確認／確定利益・報酬は算出不可",
    )
    return order_row, line_rows


def replace_sheet(book, name, headers, rows):
    if name in book:
        del book[name]
    sheet = book.create_sheet(name)
    sheet.append(headers)
    for row in rows:
        sheet.append(tuple(excel_text(value) for value in row))
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions


def update_workbook(source: Path, target: Path, items, orders, start: date, end: date):
    book = load_workbook(source)
    if SHEET_PRICES not in book or SHEET_STOCK not in book:
        raise SyncError("指定台帳に ③-3 または ③-4 シートがありません")
    prices, stock = book[SHEET_PRICES], book[SHEET_STOCK]
    price_rows = {}
    stock_rows = {}
    for row in range(9, 44):
        key = prices.cell(row, 1).value
        if isinstance(key, str) and key.startswith("BASE:"):
            item_id = int(key[5:])
            if item_id in price_rows:
                raise SyncError("③-3 に商品 ID の重複があります")
            price_rows[item_id] = row
    for row in range(8, 19):
        item_id = stock.cell(row, 2).value
        if item_id is not None:
            item_id = int(item_id)
            if item_id in stock_rows:
                raise SyncError("③-4 に商品 ID の重複があります")
            stock_rows[item_id] = row
    if set(price_rows) != set(stock_rows):
        raise SyncError("③-3 と ③-4 の商品 ID 対応が不一致")
    item_rows = []
    for item_id, item in sorted(items.items()):
        matched = item_id in price_rows
        variants = item["variations"] or [None]
        for variant in variants:
            item_rows.append((item_id, excel_text(item["name"]), excel_text(item.get("identifier")), item["price"], item["stock"],
                              None if variant is None else variant["id"], None if variant is None else excel_text(variant.get("name")),
                              item["stock"] if variant is None else variant["stock"],
                              None if variant is None else excel_text(variant.get("identifier")),
                              "台帳連携" if matched else "台帳未登録"))
        if matched:
            stock.cell(stock_rows[item_id], 3, excel_text(item["name"]))
            stock.cell(stock_rows[item_id], 4, item["stock"])
            prices.cell(price_rows[item_id], 3, excel_text(item["name"]))
            prices.cell(price_rows[item_id], 5).value = item["price"]
    order_rows = []
    line_rows = []
    for key in sorted(orders):
        order_row, lines = normalize_order(orders[key])
        order_rows.append(order_row)
        line_rows.extend(lines)
    replace_sheet(book, SHEET_ITEMS, ["BASE商品ID", "商品名", "商品コード", "商品価格（税込円）", "商品合計在庫", "種類ID", "種類名", "種類在庫", "種類コード", "台帳対応"], item_rows)
    replace_sheet(book, SHEET_ORDERS, ["注文キー", "注文日時UTC", "注文状態", "商品小計円", "顧客送料円", "代引手数料円", "注文合計円", "BASE徴収手数料円", "追加料金内訳", "最終発送日時UTC", "発送履歴ID:日時:明細ID", "利益・報酬判定"], order_rows)
    replace_sheet(book, SHEET_LINES, ["注文キー", "明細ID", "BASE商品ID", "種類ID", "注文時商品名", "注文時種類名", "単価円", "数量", "明細合計円", "明細状態", "顧客送料配分円"], line_rows)
    replace_sheet(book, SHEET_RUN, ["項目", "値"], [
        ("商品取得", "完了"), ("商品件数", len(items)), ("注文取得", "完了（期間内0件）" if not orders else "完了"),
        ("注文期間開始JST", start.isoformat()), ("注文期間終了JST", end.isoformat()), ("注文件数", len(orders)),
        ("商品台帳未登録件数", len(set(items) - set(price_rows))),
        ("台帳商品未取得件数", len(set(price_rows) - set(items))),
        ("注記", "台帳商品未取得行は既存値を保持。0 は API が返した実在庫のみ。注文検索期間外は未取得。"),
    ])
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(suffix=".xlsx", prefix=".base_sync_", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        book.save(temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return len(set(price_rows) - set(items))


def main(argv=None):
    parser = argparse.ArgumentParser(description="BASE API v2 を読み取り、既存台帳のコピーを更新")
    parser.add_argument("--workbook", required=True, type=Path, help="既存 xlsx。出力先と同じパスも可")
    parser.add_argument("--output", required=True, type=Path, help="更新後 xlsx")
    parser.add_argument("--from-date", required=True, type=date.fromisoformat, help="注文の開始日（JST、YYYY-MM-DD）")
    parser.add_argument("--to-date", required=True, type=date.fromisoformat, help="注文の終了日（JST、YYYY-MM-DD）")
    args = parser.parse_args(argv)
    try:
        if not args.workbook.is_file():
            raise SyncError("入力台帳がありません")
        if not valid_order_range(args.from_date, args.to_date):
            raise SyncError("注文期間は開始日から 1 年未満にしてください")
        client = BaseClient(os.environ.get("BASE_PAT", ""))
        items = client.items()
        orders = client.orders(args.from_date, args.to_date)
        missing = update_workbook(args.workbook, args.output, items, orders, args.from_date, args.to_date)
        print(f"完了: 商品 {len(items)} 件、注文 {len(orders)} 件。台帳商品未取得 {missing} 件。出力: {args.output}")
        return 0
    except (SyncError, OSError) as exc:
        print(f"中断: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
