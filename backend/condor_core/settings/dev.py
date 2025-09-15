# condor_core/settings/dev.py
from .base import *
import os
# Dev por ENV (no hardcode)
# DEBUG ya viene de base vía DJANGO_DEBUG
CORS_ALLOW_ALL_ORIGINS = True  # práctico en dev; si querés, controlalo por ENV

OAUTH_AUTO_PROVISION = os.getenv("OAUTH_AUTO_PROVISION", "false").lower() == "true"
OAUTH_ALLOWED_EMAIL_DOMAIN = os.getenv("OAUTH_ALLOWED_EMAIL_DOMAIN", "*")
TENANT_STRICT_HOST = True
OAUTH_REQUIRE_EMAIL_VERIFIED = True
OAUTH_ALLOWED_EMAIL_DOMAIN = "*" 
NOTIF_EMAIL_ENABLED = True                 # habilita el envío real
AWS_REGION = "us-east-1"                   # tu región SES
NOTIF_EMAIL_FROM = "notificaciones@cnd-ia.com"  # remitente verificado en SES
SES_CONFIGURATION_SET = None  