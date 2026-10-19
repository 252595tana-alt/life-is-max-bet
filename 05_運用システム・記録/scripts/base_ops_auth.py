"""Exchange a service-account assertion for a short-lived Sheets token.

The JSON credential is read only from GOOGLE_SERVICE_ACCOUNT_JSON in memory.
Neither the private key nor the returned token is printed or written to disk.
"""

from __future__ import annotations

import base64
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from base_ledger_sync import SyncError


TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def _part(data):
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def token_from_service_account(credential_json: str, now=None):
    """Mint one access token via the OAuth JWT bearer grant."""
    try:
        credential = json.loads(credential_json)
        if credential.get("type") != "service_account" or credential.get("token_uri") != TOKEN_URI:
            raise ValueError("credential type or token URI")
        email = credential["client_email"]
        key_pem = credential["private_key"].encode("ascii")
        if not isinstance(email, str) or not email.endswith(".gserviceaccount.com"):
            raise ValueError("client email")
        private_key = serialization.load_pem_private_key(key_pem, password=None)
    except (KeyError, TypeError, ValueError):
        raise SyncError("Googleサービスアカウント認証設定が不正") from None
    current = int(time.time() if now is None else now)
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {"iss": email, "scope": SCOPE, "aud": TOKEN_URI,
             "iat": current, "exp": current + 3500}
    signing_input = (_part(header) + "." + _part(claim)).encode("ascii")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    assertion = signing_input.decode("ascii") + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    body = urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                      "assertion": assertion}).encode("ascii")
    request = Request(TOKEN_URI, data=body, method="POST",
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError):
        raise SyncError("Googleサービスアカウントのトークン取得失敗") from None
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise SyncError("Googleトークン応答が不正")
    return token


def token_from_env():
    credential = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not credential:
        raise SyncError("GOOGLE_SERVICE_ACCOUNT_JSON が未設定")
    return token_from_service_account(credential)
