"""Eight-tab sync contract checks; all BASE data is synthetic."""

import sys
import unittest
import json
import base64
import contextlib
import io
from datetime import date
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from base_ledger_sync import SyncError  # noqa: E402
from base_ops_sync import FORMULA_RANGES, RANGES, build_plan, snapshot_from_raw, main  # noqa: E402
from base_ops_sheets import GoogleSheetsAdapter, fingerprint  # noqa: E402
from base_ops_auth import TOKEN_URI, token_from_service_account  # noqa: E402


KEY = "ABCDEFGHIJKLMNOP"
START, END = date(2026, 10, 1), date(2026, 10, 15)


def item(stock=0, price=8800, item_id=162021520):
    return {"id": item_id, "name": "Test T-shirt", "identifier": "SKU-T",
            "price": price, "stock": stock,
            "variations": [{"id": 17, "name": "L", "identifier": "SKU-T-L",
                            "stock": stock}]}


def order(status="ordered", lines=None, dispatched_at=None):
    if lines is None:
        lines = [{"id": 7, "item_id": 162021520, "variation_id": 17,
                  "title": "Test T-shirt", "variation": "L", "price": 8800,
                  "amount": 1, "total": 8800, "status": status,
                  "shipping_fee": 780}]
    return {"unique_key": KEY, "ordered_at": "2026-10-10T01:00:00Z",
            "status": status,
            "customer": {"name": "PRIVATE_PERSON", "email": "private@example.invalid"},
            "amounts": {"subtotal": sum(x["total"] for x in lines),
                        "shipping_fee": 780, "cod_fee": 0,
                        "total": sum(x["total"] for x in lines) + 780,
                        "service_charge": {"collected_fee": 565},
                        "additional_charges": []},
            "lines": lines,
            "delivery": {"dispatched_at": dispatched_at,
                         "dispatches": [] if not dispatched_at else [
                             {"id": 19, "dispatched_at": dispatched_at,
                              "order_line_ids": [x["id"] for x in lines]}]}}


def state(existing_order=False):
    d = {name: [] for name in RANGES | FORMULA_RANGES}
    d["products"] = [["BASE:162021520", "BASE", None, "Old name", None,
                      "162021520", 8800, None, 3]]
    d["skus"] = [["VAR:17", "162021520", "Old name", "17", "L", None,
                  3, 8800]]
    d["product_status"] = [[f'=IF(D{row}="","未取得",IF(B{row}="BASE","取得済 2026/10/15","BASE未対応"))']
                           for row in range(74, 88)]
    d["visible_sku_status"] = [[f'=IF(ISNUMBER(E{row}),IF(ISNUMBER(H{row}),"取得済","取得日未確認"),"在庫未取得")']
                               for row in range(22, 50)]
    d["profit_status"] = [[f'=IF(A{row}="","",IF(AB{row}<>"有効",AB{row},IF(ISNUMBER(O{row}),"確定","未確定")))']
                          for row in range(5, 105)]
    d["order_validity"] = [[f'=IF(A{row}="","",IF(AC{row}="不一致重複","要確認除外",IF(COUNTIF($A$5:A{row},A{row})=1,"有効","重複除外")))']
                           for row in range(5, 105)]
    if existing_order:
        d["orders"] = [[KEY, "2026-10-10T01:00:00Z", "ordered", 9580,
                        None, None, None, None, None, None, 8800, 780, 0,
                        565, None, 0, "取得済", 350, 0, 0, 1200]]
        d["lines"] = [[KEY, 7, 162021520, 17, "Test T-shirt", "L",
                       8800, 1, 8800, "ordered"]]
    return d


def writes_by_range(writes):
    return {x["range"]: x["values"][0][0] for x in writes}


class OpsSyncTests(unittest.TestCase):
    def test_zero_stock_and_unretrieved_are_distinct(self):
        snap = snapshot_from_raw({162021520: item(stock=0)}, {}, "2026-10-15T00:00:00Z")
        result = writes_by_range(build_plan(snap, state(), START, END))
        self.assertEqual(result["'商品・在庫マスター'!I74"], 0)
        self.assertEqual(result["'商品・在庫マスター'!G142"], 0)
        self.assertNotIn("'商品・在庫マスター'!H74", result)  # manual cost

    def test_missing_item_does_not_zero_previous_stock(self):
        snap = snapshot_from_raw({}, {}, "2026-10-15T00:00:00Z")
        result = writes_by_range(build_plan(snap, state(), START, END))
        self.assertNotIn("'商品・在庫マスター'!I74", result)
        self.assertIn("前回値", result["'商品・在庫マスター'!K142"])
        self.assertIn("前回値", result["'商品・在庫マスター'!N74"])
        self.assertIn("前回値", result["'商品・在庫マスター'!I22"])

    def test_unmapped_id_fails_before_any_write(self):
        snap = snapshot_from_raw({99: item(item_id=99)}, {}, "2026-10-15T00:00:00Z")
        with self.assertRaises(SyncError):
            build_plan(snap, state(), START, END)

    def test_existing_order_and_line_are_upserted_by_fixed_ids(self):
        snap = snapshot_from_raw({162021520: item()}, {KEY: order()}, "2026-10-15T00:00:00Z")
        result = writes_by_range(build_plan(snap, state(existing_order=True), START, END))
        self.assertEqual(result["'受注・売上・利益'!A5"], KEY)
        self.assertEqual(result["'受注・売上・利益'!AI5"], 7)
        for manual in ("R5", "S5", "T5", "U5", "V5", "W5", "X5"):
            self.assertNotIn(f"'受注・売上・利益'!{manual}", result)

    def test_cancelled_and_refund_inputs_remain_manual(self):
        snap = snapshot_from_raw({162021520: item()}, {KEY: order(status="cancelled")},
                                 "2026-10-15T00:00:00Z")
        result = writes_by_range(build_plan(snap, state(existing_order=True), START, END))
        self.assertEqual(result["'受注・売上・利益'!C5"], "cancelled")
        self.assertNotIn("'受注・売上・利益'!S5", result)
        self.assertNotIn("'受注・売上・利益'!W5", result)

    def test_multi_line_and_dispatch_are_not_doubled(self):
        first = order()["lines"][0]
        second = dict(first, id=8, amount=2, total=17600)
        snap = snapshot_from_raw({162021520: item()},
                                 {KEY: order(status="dispatched", lines=[first, second],
                                             dispatched_at="2026-10-12T01:00:00Z")},
                                 "2026-10-15T00:00:00Z")
        result = writes_by_range(build_plan(snap, state(), START, END))
        self.assertEqual(result["'受注・売上・利益'!P5"], 1)
        self.assertEqual(result["'受注・売上・利益'!AI5"], 7)
        self.assertEqual(result["'受注・売上・利益'!AI6"], 8)
        self.assertEqual(result["'受注・売上・利益'!N5"], 565)
        self.assertIsInstance(result["'受注・売上・利益'!O5"], (int, float))
        self.assertEqual(result["'受注・売上・利益'!O5"], 46307 + 10/24)
        self.assertIsInstance(result["'受注・売上・利益'!B5"], (int, float))
        self.assertNotIn("'受注・売上・利益'!N6", result)

    def test_missing_order_is_stale_without_zero_overwrite(self):
        snap = snapshot_from_raw({162021520: item()}, {}, "2026-10-15T00:00:00Z")
        result = writes_by_range(build_plan(snap, state(existing_order=True), START, END))
        self.assertIn("前回値", result["'受注・売上・利益'!Q5"])
        self.assertNotIn("'受注・売上・利益'!D5", result)
        self.assertIn('Q5<>"取得済"', result["'受注・売上・利益'!Y5"])
        self.assertIn('Q5<>"取得済"', result["'受注・売上・利益'!AB5"])
        self.assertEqual(result["'ダッシュボード'!D7"], "10/15取得時点")

    def test_stale_numeric_order_date_and_no_freshness_on_failure(self):
        current = state(existing_order=True)
        current["orders"][0][1] = 46306.30553240741
        snap = snapshot_from_raw({162021520: item()}, {}, "2026-10-19T00:00:00Z")
        result = writes_by_range(build_plan(snap, current, START, date(2026, 10, 19)))
        self.assertEqual(result["'受注・売上・利益'!Q5"], "検索で未取得（前回値）")
        self.assertEqual(result["'受注・売上・利益'!AS5"], "検索で未取得（前回値）")
        self.assertEqual(result["'商品・在庫マスター'!A2"].split("取得")[0], "2026/10/19")
        self.assertEqual(result["'ダッシュボード'!D7"], "10/19取得時点")

    def test_orphan_manual_row_is_not_allocated(self):
        current = state()
        current["orders"] = [[""] + [None] * 16 + [999]]
        snap = snapshot_from_raw({162021520: item()}, {KEY: order()}, "2026-10-15T00:00:00Z")
        result = writes_by_range(build_plan(snap, current, START, END))
        self.assertNotIn("'受注・売上・利益'!A5", result)
        self.assertEqual(result["'受注・売上・利益'!A6"], KEY)
        self.assertNotIn("'受注・売上・利益'!R5", result)

    def test_unexpected_formula_aborts_all_writes(self):
        current = state()
        current["profit_status"][0] = ["custom"]
        snap = snapshot_from_raw({162021520: item()}, {}, "2026-10-15T00:00:00Z")
        with self.assertRaises(SyncError):
            build_plan(snap, current, START, END)

    def test_duplicate_existing_ids_abort(self):
        current = state(existing_order=True)
        current["orders"].append([KEY])
        snap = snapshot_from_raw({162021520: item()}, {KEY: order()}, "2026-10-15T00:00:00Z")
        with self.assertRaises(SyncError):
            build_plan(snap, current, START, END)

    def test_privacy_and_formula_whitelist(self):
        snap = snapshot_from_raw({162021520: item()}, {KEY: order()}, "2026-10-15T00:00:00Z")
        result = build_plan(snap, state(), START, END)
        all_text = repr((snap, result))
        self.assertNotIn("PRIVATE_PERSON", all_text)
        self.assertNotIn("private@example.invalid", all_text)
        self.assertFalse(any(x["range"].endswith("!AR5") for x in result))
        request = GoogleSheetsAdapter._request_for_cell(result[0])
        self.assertIn("userEnteredValue", request["updateCells"]["rows"][0]["values"][0])
        self.assertEqual(fingerprint(state()), fingerprint(state()))
        for forbidden in ("'作業管理'!K25", "'受注・売上・利益'!R5",
                          "'受注・売上・利益'!E5"):
            with self.assertRaises(SyncError):
                GoogleSheetsAdapter._request_for_cell({"range": forbidden, "values": [[0]]})
        with self.assertRaises(SyncError):
            GoogleSheetsAdapter._request_for_cell({"range": "'商品・在庫マスター'!N74", "values": [[0]]})
        formula_request = GoogleSheetsAdapter._request_for_cell({
            "range": "'商品・在庫マスター'!N74", "values": [[result[0]["values"][0][0]]]})
        self.assertIn("formulaValue", formula_request["updateCells"]["rows"][0]["values"][0]["userEnteredValue"])

    def test_reread_failure_does_not_advance_success_marker(self):
        adapter = GoogleSheetsAdapter("synthetic", "1bB-pnCvqC9svrwZgquCFHMqW0vJqMypM2w3pEaxcTl0")
        with patch.object(adapter, "read_current", side_effect=SyncError("read failed")), \
                patch.object(adapter, "_request") as request:
            with self.assertRaises(SyncError):
                adapter.apply_if_unchanged([], fingerprint(state()), "2026-10-19T00:00:00Z")
        request.assert_not_called()

    def test_data_and_freshness_are_one_batch(self):
        adapter = GoogleSheetsAdapter("synthetic", "1bB-pnCvqC9svrwZgquCFHMqW0vJqMypM2w3pEaxcTl0")
        planned = [{"range": "'受注・売上・利益'!Q5", "values": [["取得済"]]},
                   {"range": "'ダッシュボード'!D7", "values": [["10/19取得時点"]]}]
        with patch.object(adapter, "read_current", return_value=state()), \
                patch.object(adapter, "_request", return_value={}) as request:
            adapter.apply_if_unchanged(planned, fingerprint(state()), "2026-10-19T00:00:00Z")
        self.assertEqual(request.call_count, 1)
        method, endpoint, body = request.call_args.args
        self.assertEqual((method, endpoint), ("POST", ":batchUpdate"))
        self.assertEqual(len(body["requests"]), len(planned) + 4)

    def test_mismatched_state_does_not_submit_batch(self):
        adapter = GoogleSheetsAdapter("synthetic", "1bB-pnCvqC9svrwZgquCFHMqW0vJqMypM2w3pEaxcTl0")
        with patch.object(adapter, "read_current", return_value=state()), \
                patch.object(adapter, "_request") as request:
            with self.assertRaises(SyncError):
                adapter.apply_if_unchanged([], "different", "2026-10-19T00:00:00Z")
        request.assert_not_called()

    def test_guarded_formulas_are_idempotent(self):
        current = state(existing_order=True)
        snap = snapshot_from_raw({162021520: item()}, {KEY: order()}, "2026-10-15T00:00:00Z")
        first = writes_by_range(build_plan(snap, current, START, END))
        for name, column in (("profit_status", "Y"), ("order_validity", "AB")):
            current[name][0] = [first[f"'受注・売上・利益'!{column}5"]]
        second = writes_by_range(build_plan(snap, current, START, END))
        self.assertNotIn("'受注・売上・利益'!Y5", second)
        self.assertNotIn("'受注・売上・利益'!AB5", second)

    def test_service_account_uses_short_lived_scoped_token(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(serialization.Encoding.PEM,
                                serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode("ascii")
        credential = json.dumps({"type": "service_account", "token_uri": TOKEN_URI,
                                 "client_email": "test@demo.gserviceaccount.com",
                                 "private_key": pem})

        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b'{"access_token":"synthetic-access-token"}'

        with patch("base_ops_auth.urlopen", return_value=Reply()) as mocked:
            token = token_from_service_account(credential, now=1_700_000_000)
        self.assertEqual(token, "synthetic-access-token")
        body = mocked.call_args.args[0].data.decode("ascii")
        from urllib.parse import parse_qs
        assertion = parse_qs(body)["assertion"][0]
        claim_raw = assertion.split(".")[1]
        claim = json.loads(base64.urlsafe_b64decode(claim_raw + "=="))
        self.assertEqual(claim["exp"] - claim["iat"], 3500)
        self.assertEqual(claim["scope"], "https://www.googleapis.com/auth/spreadsheets")

    def test_base_failure_never_touches_native_or_prints_secret(self):
        stderr = io.StringIO()
        with patch("base_ops_sync.BaseClient") as client, \
                patch("base_ops_sheets.GoogleSheetsAdapter") as sheet, \
                patch.dict("os.environ", {"BASE_PAT": "synthetic-secret"}), \
                contextlib.redirect_stderr(stderr):
            client.return_value.items.side_effect = SyncError("synthetic-secret private@example.invalid")
            code = main(["--from-date", "2026-10-01", "--to-date", "2026-10-15",
                         "--sheet-id", "1bB-pnCvqC9svrwZgquCFHMqW0vJqMypM2w3pEaxcTl0"])
        self.assertEqual(code, 2)
        sheet.assert_not_called()
        self.assertNotIn("synthetic-secret", stderr.getvalue())
        self.assertNotIn("private@example.invalid", stderr.getvalue())

    def test_order_fetch_failure_after_items_does_not_touch_native(self):
        with patch("base_ops_sync.BaseClient") as client, \
                patch("base_ops_sheets.GoogleSheetsAdapter") as sheet, \
                patch.dict("os.environ", {"BASE_PAT": "synthetic-secret"}), \
                contextlib.redirect_stderr(io.StringIO()):
            client.return_value.items.return_value = {162021520: item()}
            client.return_value.orders.side_effect = SyncError("order fetch failed")
            code = main(["--from-date", "2026-10-01", "--to-date", "2026-10-15",
                         "--sheet-id", "1bB-pnCvqC9svrwZgquCFHMqW0vJqMypM2w3pEaxcTl0"])
        self.assertEqual(code, 2)
        sheet.assert_not_called()


if __name__ == "__main__":
    unittest.main()
