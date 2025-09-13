# apps/auth_core/oauth.py
import os
from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class GoogleOIDCConfig:
    client_id: str
    client_secret: str
    issuer: str
    jwks_url: str
    redirect_uri: str
    state_hmac_secret: str

    @classmethod
    def from_env(cls) -> "GoogleOIDCConfig":
        return cls(
            client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            issuer=os.environ.get("GOOGLE_ISSUER", "https://accounts.google.com"),
            jwks_url=os.environ.get("GOOGLE_JWKS_URL", "https://www.googleapis.com/oauth2/v3/certs"),
            redirect_uri=os.environ.get("OAUTH_REDIRECT_URI", ""),
            state_hmac_secret=os.environ.get("STATE_HMAC_SECRET", ""),
        )

    def validate(self) -> List[str]:
        errs: List[str] = []
        if not self.client_id: errs.append("Missing GOOGLE_CLIENT_ID")
        if not self.client_secret: errs.append("Missing GOOGLE_CLIENT_SECRET")
        if not self.issuer.startswith("https://accounts.google.com"):
            errs.append(f"Unexpected GOOGLE_ISSUER={self.issuer}")
        if not (self.jwks_url.startswith("https://") and "googleapis.com" in self.jwks_url):
            errs.append("Invalid GOOGLE_JWKS_URL")
        if not (self.redirect_uri.startswith("http://") or self.redirect_uri.startswith("https://")):
            errs.append("Invalid OAUTH_REDIRECT_URI")
        if len(self.state_hmac_secret) < 32:
            errs.append("STATE_HMAC_SECRET too short (>=32)")
        return errs
