# apps/auth_core/management/commands/check_oauth_config.py
import hashlib
import json
import logging
from urllib.request import urlopen, Request
from urllib.error import URLError
from django.core.management.base import BaseCommand, CommandError
from apps.auth_core.oauth import GoogleOIDCConfig

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Verifica envs de Google OIDC y reachability JWKS (sin exponer secretos)."

    def handle(self, *args, **options):
        cfg = GoogleOIDCConfig.from_env()
        errs = cfg.validate()
        if errs:
            for e in errs:
                self.stdout.write(self.style.ERROR(f"[OAUTH CHECK] {e}"))
            raise CommandError("Configuración OIDC inválida.")

        client_hash = hashlib.sha256(cfg.client_id.encode()).hexdigest()[:12]
        self.stdout.write(self.style.SUCCESS("[OAUTH CHECK] Variables de entorno OK."))
        self.stdout.write(f"[OAUTH CHECK] client_id_hash={client_hash}")
        self.stdout.write(f"[OAUTH CHECK] issuer={cfg.issuer}")
        self.stdout.write(f"[OAUTH CHECK] jwks_url={cfg.jwks_url}")
        self.stdout.write(f"[OAUTH CHECK] redirect_uri={cfg.redirect_uri}")

        try:
            req = Request(cfg.jwks_url, headers={"User-Agent": "condor-oauth-check/1.0"})
            with urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                keys = data.get("keys", [])
                self.stdout.write(self.style.SUCCESS(f"[OAUTH CHECK] JWKS reachable. keys={len(keys)}"))
        except URLError as ex:
            self.stdout.write(self.style.WARNING(f"[OAUTH CHECK] No se pudo acceder a JWKS: {ex}"))
            self.stdout.write(self.style.WARNING("[OAUTH CHECK] Podés continuar, pero verificá conectividad de red."))

        self.stdout.write(self.style.SUCCESS("[DONE] Chequeo OIDC completado."))
