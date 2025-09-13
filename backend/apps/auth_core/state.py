# apps/auth_core/state.py
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Tuple

# Base64 URL-safe sin "="
def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _b64u_dec(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def sign_state(payload: Dict[str, Any], secret: str, ttl_seconds: int = 300) -> str:
    body = dict(payload)
    body["ts"] = int(time.time())
    body["exp"] = body["ts"] + ttl_seconds
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).digest()
    return _b64u(raw) + "." + _b64u(sig)

def verify_state(state: str, secret: str) -> Tuple[Dict[str, Any], str]:
    """Devuelve (payload, reason='') o lanza ValueError si no es válido."""
    try:
        raw_b64, sig_b64 = state.split(".", 1)
    except ValueError:
        raise ValueError("state_format_invalid")
    raw = _b64u_dec(raw_b64)
    expected_sig = hmac.new(secret.encode(), raw, hashlib.sha256).digest()
    got_sig = _b64u_dec(sig_b64)
    if not hmac.compare_digest(expected_sig, got_sig):
        raise ValueError("state_hmac_invalid")
    payload = json.loads(raw.decode())
    now = int(time.time())
    if "exp" not in payload or now > int(payload["exp"]):
        raise ValueError("state_expired")
    return payload, ""
