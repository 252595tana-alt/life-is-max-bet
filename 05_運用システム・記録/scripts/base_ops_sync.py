"""Plan a read-only BASE v2 sync for the eight-tab operations sheet.

The default command creates a redacted plan only.  The cloud writer is opt-in
and must not be enabled until the new sheet has been chosen as the source of
truth and its access token has been configured.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from base_ledger_sync import BaseClient, SyncError, normalize_order, valid_order_range


SHEET_ID = "1bB-pnCvqC9svrwZgquCFHMqW0vJqMypM2w3pEaxcTl0"
STOCK = "商品・在庫マスター"
SALES = "受注・売上・利益"
RANGES = {
    "products": f"'{STOCK}'!A74:V87",
    "skus": f"'{STOCK}'!A142:L169",
    "orders": f"'{SALES}'!A5:AG104",
    "lines": f"'{SALES}'!AH5:AS104",
}
FORMULA_RANGES = {
    "product_status": f"'{STOCK}'!N74:N87",
    "visible_sku_status": f"'{STOCK}'!I22:I49",
    "profit_status": f"'{SALES}'!Y5:Y104",
    "order_validity": f"'{SALES}'!AB5:AB104",
}
STALE = "検索で未取得（前回値）"
JST = timezone(timedelta(hours=9))


def _text(value, field):
    if not isinstance(value, str):
        raise SyncError(f"{field} が不正")
    return "'" + value if value.startswith(("=", "+", "-", "@")) else value


def _int(value, field):
    if type(value) is not int or value < 0:
        raise SyncError(f"{field} が未取得または不正")
    return value


def normalize_items(raw_items):
    """Return only product and SKU fields; never persist the API response."""
    items, skus = {}, {}
    for item_id, raw in raw_items.items():
        if type(item_id) is not int or raw.get("id") != item_id:
            raise SyncError("商品 ID が不整合")
        price = raw.get("price")
        if price is not None:
            price = _int(price, "商品.price")
        stock = _int(raw.get("stock"), "商品.stock")
        name = _text(raw.get("name"), "商品.name")
        identifier = raw.get("identifier")
        if identifier is not None:
            identifier = _text(identifier, "商品.identifier")
        items[item_id] = {"name": name, "price": price, "stock": stock}
        variations = raw.get("variations")
        if not isinstance(variations, list):
            raise SyncError("種類一覧が未取得")
        if not variations:
            key = f"ITEM:{item_id}|NO-VARIATION"
            skus[key] = {"item_id": item_id, "name": name,
                         "variation": None, "identifier": identifier,
                         "stock": stock, "price": price}
            continue
        for variation in variations:
            variation_id = _int(variation.get("id"), "種類.id")
            key = f"VAR:{variation_id}"
            if key in skus:
                raise SyncError("種類 ID が重複")
            variation_price = variation.get("price", price)
            if variation_price is not None:
                variation_price = _int(variation_price, "種類.price")
            variation_identifier = variation.get("identifier")
            if variation_identifier is not None:
                variation_identifier = _text(variation_identifier, "種類.identifier")
            skus[key] = {
                "item_id": item_id, "name": name,
                "variation": _text(variation.get("name") or "", "種類.name"),
                "identifier": variation_identifier,
                "stock": _int(variation.get("stock"), "種類.stock"),
                "price": variation_price,
            }
        if sum(v["stock"] for v in skus.values() if v["item_id"] == item_id) != stock:
            raise SyncError("商品合計と種類別在庫が不一致")
    return items, skus


def normalize_orders(raw_orders):
    """Whitelist order/line fields; buyer data is discarded in memory."""
    orders, lines = {}, {}
    for key, detail in raw_orders.items():
        if detail.get("unique_key") != key:
            raise SyncError("注文キーが不整合")
        order_row, line_rows = normalize_order(detail)
        if order_row[2] not in ("ordered", "dispatched", "cancelled", "arrived"):
            raise SyncError("注文状態が未対応")
        orders[key] = {
            "ordered_at": order_row[1], "status": order_row[2],
            "subtotal": order_row[3], "shipping_fee": order_row[4],
            "cod_fee": order_row[5], "total": order_row[6],
            "fee": order_row[7], "dispatched_at": order_row[9],
            "dispatch_count": order_row[12],
        }
        for row in line_rows:
            pair = (key, row[1])
            if pair in lines:
                raise SyncError("注文明細キーが重複")
            lines[pair] = {
                "item_id": row[2], "variation_id": row[3],
                "title": row[4], "variation": row[5],
                "price": row[6], "quantity": row[7],
                "total": row[8], "status": row[9],
            }
    return orders, lines


@dataclass(frozen=True)
class Snapshot:
    items: dict
    skus: dict
    orders: dict
    lines: dict
    fetched_at: str


def snapshot_from_raw(items, orders, fetched_at=None):
    products, skus = normalize_items(items)
    normalized_orders, lines = normalize_orders(orders)
    stamp = fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    return Snapshot(products, skus, normalized_orders, lines, stamp)


def cell(rows, index, column):
    row = rows[index] if index < len(rows) else []
    return row[column] if column < len(row) else ""


def _date_only(stamp):
    return _jst_datetime(stamp).date().isoformat()


def _jst_datetime(stamp):
    if not isinstance(stamp, str):
        raise SyncError("API日時が不正")
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        raise SyncError("API日時が不正") from None
    if parsed.tzinfo is None:
        raise SyncError("API日時にタイムゾーンがない")
    return parsed.astimezone(JST)


def _datetime_serial(stamp):
    if stamp is None or stamp == "":
        return ""
    local = _jst_datetime(stamp)
    base = datetime(1899, 12, 30, tzinfo=JST)
    return (local - base).total_seconds() / 86400


def _date_serial(stamp):
    """Sheets/Excel day serial for preformatted date cells."""
    return (date.fromisoformat(_date_only(stamp)) - date(1899, 12, 30)).days


def _ordered_in_range(value, start, end):
    try:
        if type(value) in (int, float):
            ordered_day = (datetime(1899, 12, 30) + timedelta(days=value)).date()
        elif isinstance(value, str):
            ordered_day = _jst_datetime(value).date()
        else:
            return False
        return start <= ordered_day <= end
    except (OverflowError, ValueError, SyncError):
        return False


def _free_row(rows, index, count):
    # A blank ID is insufficient: manual fees may remain on an orphan row.
    return all(cell(rows, index, column) in ("", None) for column in range(count))


def _sheet_cell(sheet, column, row, value):
    # Values API RAW: leading '=' remains literal user data; no formulas injected.
    return {"range": f"'{sheet}'!{column}{row}", "values": [[value if value is not None else ""]]}


def _guarded_formula(original, row, column):
    if not isinstance(original, str) or not original.startswith(f'=IF(A{row}="","",'):
        raise SyncError(f"{column}列の既存計算式が想定外。自動同期を中止")
    required = (f'AB{row}', f'ISNUMBER(O{row})') if column == "Y" else (f'AC{row}', f'COUNTIF($A$5:A{row},A{row})')
    if not all(marker in original for marker in required):
        raise SyncError(f"{column}列の既存計算式が想定外。自動同期を中止")
    state = "未確定" if column == "Y" else "取得状態要確認"
    guarded_prefix = f'=IF(A{row}="","",IF(Q{row}<>"取得済","{state}",'
    if original.startswith(guarded_prefix):
        return original
    return f'=IF(A{row}="","",IF(Q{row}<>"取得済","{state}",{original[1:]}))'


def _product_status_formula(row):
    return (f'=IF(D{row}="","未取得",IF(B{row}="BASE",'
            f'IF(COUNTIFS($B$142:$B$169,F{row},$K$142:$K$169,"{STALE}")>0,"前回値",'
            f'IF(COUNTIFS($B$142:$B$169,F{row},$J$142:$J$169,">0")=0,"未取得",'
            f'"取得済 "&TEXT(MAXIFS($J$142:$J$169,$B$142:$B$169,F{row}),"yyyy/mm/dd"))),'
            '"BASE未対応"))')


def _visible_sku_status_formula(row):
    return (f'=IF(J{row}="{STALE}","前回値",'
            f'IF(ISNUMBER(E{row}),IF(ISNUMBER(H{row}),"取得済","取得日未確認"),"在庫未取得"))')


def build_plan(snapshot: Snapshot, current: dict, start: date, end: date):
    """Fail closed on unknown IDs/capacity before returning any writes.

    `current` contains UNFORMATTED_VALUE rows for exactly RANGES. Formula and
    manual columns are never in the returned writes.
    """
    if not valid_order_range(start, end):
        raise SyncError("注文期間は開始日から1年未満")
    if set(current) != set(RANGES) | set(FORMULA_RANGES):
        raise SyncError("必要なシート範囲が未取得")
    product_rows = current["products"]
    sku_rows = current["skus"]
    order_rows = current["orders"]
    line_rows = current["lines"]
    product_index, sku_index, order_index, line_index = {}, {}, {}, {}
    for i in range(14):
        raw_id = cell(product_rows, i, 5)
        if str(raw_id).isdigit():
            item_id = int(raw_id)
            if item_id in product_index:
                raise SyncError("商品マスター ID が重複")
            product_index[item_id] = 74 + i
    for i in range(28):
        key = cell(sku_rows, i, 0)
        if key:
            if key in sku_index:
                raise SyncError("種類マスターキーが重複")
            sku_index[key] = 142 + i
    for i in range(100):
        key = cell(order_rows, i, 0)
        if key:
            if key in order_index:
                raise SyncError("注文台帳キーが重複。自動同期を中止")
            order_index[key] = 5 + i
    for i in range(100):
        key, raw_line_id = cell(line_rows, i, 0), cell(line_rows, i, 1)
        if key or raw_line_id:
            pair = (str(key), str(raw_line_id))
            if pair in line_index:
                raise SyncError("明細台帳キーが重複。自動同期を中止")
            line_index[pair] = 5 + i

    missing_products = set(snapshot.items) - set(product_index)
    missing_skus = set(snapshot.skus) - set(sku_index)
    free_orders = [5 + i for i in range(100) if _free_row(order_rows, i, 33)]
    free_lines = [5 + i for i in range(100) if _free_row(line_rows, i, 12)]
    needed_orders = len(set(snapshot.orders) - set(order_index))
    needed_lines = len({(k, str(n)) for k, n in snapshot.lines} - set(line_index))
    if missing_products or missing_skus or needed_orders > len(free_orders) or needed_lines > len(free_lines):
        raise SyncError("新規商品・種類のID対応または注文/明細の空き行が不足。台帳は変更しません")

    writes = []
    put = lambda sheet, column, row, value: writes.append(_sheet_cell(sheet, column, row, value))
    day = _date_only(snapshot.fetched_at)
    day_serial = _date_serial(snapshot.fetched_at)
    for i in range(14):
        row = 74 + i
        original = cell(current["product_status"], i, 0)
        old_pattern = (rf'=IF\(D{row}="","未取得",IF\(B{row}="BASE",'
                       r'"取得済 [0-9]{4}/[0-9]{2}/[0-9]{2}","BASE未対応"\)\)')
        revised = _product_status_formula(row)
        if not isinstance(original, str) or (original != revised and not re.fullmatch(old_pattern, original)):
            raise SyncError("商品取得状態の既存計算式が想定外")
        if original != revised:
            put(STOCK, "N", row, revised)
    for i in range(28):
        row = 22 + i
        original = cell(current["visible_sku_status"], i, 0)
        old = (f'=IF(ISNUMBER(E{row}),IF(ISNUMBER(H{row}),"取得済","取得日未確認"),'
               '"在庫未取得")')
        revised = _visible_sku_status_formula(row)
        if original not in (old, revised):
            raise SyncError("種類取得状態の既存計算式が想定外")
        if original != revised:
            put(STOCK, "I", row, revised)
    for column, name in (("Y", "profit_status"), ("AB", "order_validity")):
        for i in range(100):
            row = 5 + i
            original = cell(current[name], i, 0)
            revised = _guarded_formula(original, row, column)
            if original != revised:
                put(SALES, column, row, revised)
    for item_id, product in snapshot.items.items():
        row = product_index[item_id]
        for column, value in (("D", product["name"]), ("G", product["price"]),
                              ("I", product["stock"])):
            put(STOCK, column, row, value)
    # The status formulas above retain the existing calculations with a Q/K freshness guard.
    for key, sku in snapshot.skus.items():
        row = sku_index[key]
        for column, value in (("C", sku["name"]), ("E", sku["variation"]),
                              ("F", sku["identifier"]), ("G", sku["stock"]),
                              ("H", sku["price"]), ("J", day_serial),
                              ("K", "BASE種類ID" if key.startswith("VAR:") else "種類ID未取得")):
            put(STOCK, column, row, value)
    for key, row in sku_index.items():
        if key not in snapshot.skus:
            put(STOCK, "K", row, STALE)
    for key, order in snapshot.orders.items():
        row = order_index.get(key)
        if row is None:
            row = free_orders.pop(0)
        for column, value in (("A", key), ("B", _datetime_serial(order["ordered_at"])),
                              ("C", order["status"]), ("D", order["total"]),
                              ("K", order["subtotal"]), ("L", order["shipping_fee"]),
                              ("M", order["cod_fee"]), ("N", order["fee"]),
                              ("O", _datetime_serial(order["dispatched_at"])),
                              ("P", order["dispatch_count"]), ("Q", "取得済"),
                              ("AA", day_serial)):
            put(SALES, column, row, value)
    for key, row in order_index.items():
        if key not in snapshot.orders and _ordered_in_range(cell(order_rows, row - 5, 1), start, end):
            put(SALES, "Q", row, STALE)
    for (key, line_id), line in snapshot.lines.items():
        pair = (key, str(line_id))
        row = line_index.get(pair)
        if row is None:
            row = free_lines.pop(0)
        for column, value in (("AH", key), ("AI", line_id),
                              ("AJ", line["item_id"]), ("AK", line["variation_id"]),
                              ("AL", line["title"]), ("AM", line["variation"]),
                              ("AN", line["price"]), ("AO", line["quantity"]),
                              ("AP", line["total"]), ("AQ", line["status"]),
                              ("AS", "取得済")):
            put(SALES, column, row, value)
        # AR5:AR104 duplicate formulas already exist in every blank slot.
    fetched_line_keys = {(k, str(n)) for k, n in snapshot.lines}
    for pair, row in line_index.items():
        if ((pair[0] in snapshot.orders and pair not in fetched_line_keys)
                or (pair[0] in order_index and pair[0] not in snapshot.orders
                    and _ordered_in_range(cell(order_rows, order_index[pair[0]] - 5, 1), start, end))):
            put(SALES, "AS", row, STALE)
    # A2 and D7 are status captions, updated in the same atomic batch as data.
    partial_stock = bool(set(sku_index) - set(snapshot.skus))
    put(STOCK, "A", 2, f'{day.replace("-", "/")}取得｜種類別在庫。商品別・撮影入力は＋で展開しV列へ。'
        + ("一部前回値。" if partial_stock else ""))
    put("ダッシュボード", "D", 7, f'{day[5:7]}/{day[8:10]}取得'
        + ("・一部前回値" if partial_stock else "時点"))
    # A batch is generated only after every capacity/identity check has passed.
    return writes


def redacted_summary(snapshot: Snapshot, writes):
    return {"items": len(snapshot.items), "skus": len(snapshot.skus),
            "orders": len(snapshot.orders), "lines": len(snapshot.lines),
            "planned_cells": len(writes), "fetched_at": snapshot.fetched_at,
            "status": "plan_only_no_sheet_write"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="BASE v2 → 新運営表の書込計画（既定は無書込）")
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--to-date", type=date.fromisoformat, required=True)
    parser.add_argument("--fixture", type=Path, help="個人情報を含まないテストJSONのみ")
    parser.add_argument("--state-fixture", type=Path, help="テスト用シート範囲JSON")
    parser.add_argument("--sheet-id", help="Google native 表のID。省略時はシートを読まない")
    parser.add_argument("--apply", action="store_true", help="計画を再照合後にnative表へ反映")
    args = parser.parse_args(argv)
    try:
        if args.apply and (not args.sheet_id or args.fixture or args.state_fixture):
            raise SyncError("--apply は実データ・nativeシート指定時のみ利用可能")
        if args.fixture:
            raw = json.loads(args.fixture.read_text(encoding="utf-8"))
            items = {int(x["id"]): x for x in raw["items"]}
            orders = {x["unique_key"]: x for x in raw["orders"]}
        else:
            client = BaseClient(os.environ.get("BASE_PAT", ""))
            items = client.items()
            orders = client.orders(args.from_date, args.to_date)
        snapshot = snapshot_from_raw(items, orders)
        if not args.state_fixture and not args.sheet_id:
            print(json.dumps({"items": len(snapshot.items), "skus": len(snapshot.skus),
                              "orders": len(snapshot.orders), "lines": len(snapshot.lines),
                              "status": "normalized_no_sheet_write"}, ensure_ascii=False))
            return 0
        adapter = None
        if args.state_fixture:
            current = json.loads(args.state_fixture.read_text(encoding="utf-8"))
        else:
            from base_ops_sheets import GoogleSheetsAdapter
            sheet_token = os.environ.get("GOOGLE_SHEETS_ACCESS_TOKEN")
            if not sheet_token:
                from base_ops_auth import token_from_env
                sheet_token = token_from_env()
            adapter = GoogleSheetsAdapter(sheet_token, args.sheet_id)
            current = adapter.read_current()
        writes = build_plan(snapshot, current, args.from_date, args.to_date)
        if args.apply:
            from base_ops_sheets import fingerprint
            adapter.apply_if_unchanged(writes, fingerprint(current), snapshot.fetched_at)
        summary = redacted_summary(snapshot, writes)
        if args.apply:
            summary["status"] = "applied_native"
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except (SyncError, KeyError, ValueError) as exc:
        # Never echo API payloads, token, buyer data, or fixture paths.
        print(f"同期中止: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
