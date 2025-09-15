# condor_core/settings/prod.py
from .base import *
import os

DEBUG = False

# --- Seguridad básica ---
SECURE_SSL_REDIRECT = os.getenv('DJANGO_SSL_REDIRECT', 'True') == 'True'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('DJANGO_HSTS_INCLUDE_SUBDOMAINS', 'False') == 'True'
SECURE_HSTS_PRELOAD = os.getenv('DJANGO_HSTS_PRELOAD', 'False') == 'True'
SECURE_REFERRER_POLICY = os.getenv('DJANGO_SECURE_REFERRER_POLICY', 'no-referrer-when-downgrade')
X_FRAME_OPTIONS = os.getenv('DJANGO_X_FRAME_OPTIONS', 'DENY')
SESSION_COOKIE_SAMESITE = os.getenv('DJANGO_SESSION_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.getenv('DJANGO_CSRF_SAMESITE', 'Lax')

# Proxy confiable (Nginx)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# CSRF (con esquema; podés usar wildcard)
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o]
# Ej. en env: CSRF_TRUSTED_ORIGINS="https://*.cnd-ia.com"

# En prod exigimos DB real
if not os.getenv('DATABASE_URL') and not os.getenv('POSTGRES_DB'):
    raise RuntimeError("Configura DATABASE_URL o variables POSTGRES_* en producción.")

# Logs JSON por defecto
if 'DJANGO_LOG_FORMAT' not in os.environ:
    os.environ['DJANGO_LOG_FORMAT'] = 'json'

# --- Cache (Redis) ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/0"),
    }
}

# --- Tenancy (para TenantMiddleware) ---
TENANT_STRICT_HOST = os.getenv("TENANT_STRICT_HOST", "True") == "True"
TENANT_TRUST_PROXY_HEADERS = os.getenv("TENANT_TRUST_PROXY_HEADERS", "True") == "True"
TENANT_CACHE_TTL_SECONDS = int(os.getenv("TENANT_CACHE_TTL_SECONDS", "300"))
TENANT_DEFAULT_CLIENTE_ID = os.getenv("TENANT_DEFAULT_CLIENTE_ID")  # sólo si strict=False

# --- OAuth / OIDC ---
GOOGLE_ISSUER = os.getenv("GOOGLE_ISSUER", "https://accounts.google.com")
GOOGLE_JWKS_URL = os.getenv("GOOGLE_JWKS_URL", "https://www.googleapis.com/oauth2/v3/certs")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "")
OAUTH_AUTO_PROVISION = os.getenv("OAUTH_AUTO_PROVISION", "false").lower() == "true"
OAUTH_ALLOWED_EMAIL_DOMAIN = os.getenv("OAUTH_ALLOWED_EMAIL_DOMAIN", "*")
OAUTH_REQUIRE_EMAIL_VERIFIED = os.getenv("OAUTH_REQUIRE_EMAIL_VERIFIED", "true").lower() == "true"
FEATURE_OAUTH_INVITES = os.getenv("FEATURE_OAUTH_INVITES", "false").lower() == "true"


NOTIF_EMAIL_ENABLED = True                 # habilita el envío real
AWS_REGION = "us-east-1"                   # tu región SES
NOTIF_EMAIL_FROM = "notificaciones@cnd-ia.com"  # remitente verificado en SES
SES_CONFIGURATION_SET = None  