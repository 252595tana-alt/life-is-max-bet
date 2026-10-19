"""Small Google Sheets REST adapter for the BASE operations sync.

No OAuth acquisition or secret storage is performed here. The caller supplies
an already-issued short-lived access token through an environment variable.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from base_ledger_sync import SyncError
from base_ops_sync import FORMULA_RANGES, RANGES, SALES, SHEET_ID, STOCK


SHEET_IDS = {STOCK: 1385939340, SALES: 1406343513, "ダッシュボード": 1887140458}
CELL_RE = re.compile(r"^'([^']+)'!([A-Z]+)([1-9][0-9]*)$")
API = "https://sheets.googleapis.com/v4/spreadsheets/"
PRODUCT_COLUMNS = {"D", "G", "I", "N"}
SKU_COLUMNS = {"C", "E", "F", "G", "H", "J", "K"}
ORDER_COLUMNS = {"A", "B", "C", "D", "K", "L", "M", "N", "O", "P", "Q", "Y", "AA", "AB"}
LINE_COLUMNS = {"AH", "AI", "AJ", "AK", "AL", "AM", "AN", "AO", "AP", "AQ", "AS"}


def fingerprint(state):
    canonical = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GoogleSheetsAdapter:
    def __init__(self, access_token: str, spreadsheet_id: str = SHEET_ID):
        if not access_token:
            raise SyncError("GOOGLE_SHEETS_ACCESS_TOKEN が未設定")
        if spreadsheet_id != SHEET_ID:
            raise SyncError("連携先シートIDが想定と異なる")
        self._token = access_token
        self._id = spreadsheet_id

    def _request(self, method, suffix, body=None):
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(
            API + quote(self._id) + suffix,
            data=payload,
            method=method,
            headers={"Authorization": "Bearer " + self._token,
                     "Accept": "application/json",
                     **({"Content-Type": "application/json"} if payload is not None else {})},
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            raise SyncError(f"Google Sheets HTTP {exc.code}。書込状態を確認してください") from None
        except (URLError, TimeoutError, ValueError):
            raise SyncError("Google Sheets 通信/応答失敗。書込状態を確認してください") from None

    def read_current(self):
        state = {}
        for ranges, mode in ((RANGES, "UNFORMATTED_VALUE"),
                             (FORMULA_RANGES, "FORMULA")):
            params = urlencode({"ranges": list(ranges.values()),
                                "valueRenderOption": mode}, doseq=True)
            response = self._request("GET", "/values:batchGet?" + params)
            value_ranges = response.get("valueRanges")
            if not isinstance(value_ranges, list) or len(value_ranges) != len(ranges):
                raise SyncError("Sheets 範囲取得が不完全")
            for name, item in zip(ranges, value_ranges):
                if not isinstance(item.get("values", []), list):
                    raise SyncError("Sheets 範囲の形式が不正")
                state[name] = item.get("values", [])
        return state

    @staticmethod
    def _request_for_cell(write):
        match = CELL_RE.fullmatch(write["range"])
        if not match or match.group(1) not in SHEET_IDS:
            raise SyncError("許可外のセル範囲")
        sheet, letters, row = match.groups()
        row_num = int(row)
        allowed = (
            (sheet == STOCK and 74 <= row_num <= 87 and letters in PRODUCT_COLUMNS)
            or (sheet == STOCK and 22 <= row_num <= 49 and letters == "I")
            or (sheet == STOCK and row_num == 2 and letters == "A")
            or (sheet == STOCK and 142 <= row_num <= 169 and letters in SKU_COLUMNS)
            or (sheet == SALES and 5 <= row_num <= 104 and letters in ORDER_COLUMNS | LINE_COLUMNS)
            or (sheet == "ダッシュボード" and row_num == 7 and letters == "D")
            or (sheet == "ダッシュボード" and row_num in (20, 21) and letters in ("H", "I"))
        )
        if not allowed:
            raise SyncError("API更新対象外のセルを拒否")
        column = 0
        for ch in letters:
            column = column * 26 + ord(ch) - ord("A") + 1
        value = write["values"][0][0]
        formula_cell = ((sheet == STOCK and letters == "N" and 74 <= row_num <= 87)
                        or (sheet == STOCK and letters == "I" and 22 <= row_num <= 49)
                        or (sheet == SALES and letters in ("Y", "AB") and 5 <= row_num <= 104))
        if formula_cell and (not isinstance(value, str) or not value.startswith("=IF(")):
            raise SyncError("計算式セルへの値書込を拒否")
        if formula_cell:
            entered = {"formulaValue": value}
        elif isinstance(value, bool):
            entered = {"boolValue": value}
        elif isinstance(value, (int, float)):
            entered = {"numberValue": value}
        else:
            entered = {"stringValue": str(value)}
        return {"updateCells": {
            "start": {"sheetId": SHEET_IDS[sheet], "rowIndex": int(row) - 1,
                      "columnIndex": column - 1},
            "rows": [{"values": [{"userEnteredValue": entered}]}],
            "fields": "userEnteredValue",
        }}

    def apply_if_unchanged(self, writes, expected_fingerprint, fetched_at):
        """Read again, then atomically submit only whitelisted API cells.

        A concurrent human edit between the second read and the Sheets commit
        cannot be ruled out by the public Values API. Operators should inspect
        the resulting run and use the source workbook as rollback reference.
        """
        if fingerprint(self.read_current()) != expected_fingerprint:
            raise SyncError("シートが計画後に変更。再計画が必要")
        requests = [self._request_for_cell(write) for write in writes]
        # These cells were verified empty in the target dashboard. They are the
        # last-success marker, not a value used by the financial formulas.
        for cell, value in (("H20", "BASE最終成功UTC"), ("I20", fetched_at),
                            ("H21", "BASE取得状態"), ("I21", "取得済")):
            requests.append(self._request_for_cell({
                "range": f"'ダッシュボード'!{cell}", "values": [[value]]}))
        self._request("POST", ":batchUpdate", {"requests": requests})


def adapter_from_env():
    return GoogleSheetsAdapter(os.environ.get("GOOGLE_SHEETS_ACCESS_TOKEN", ""))
