# condor_core/settings/dev.py
from .base import *
import os
# Dev por ENV (no hardcode)
# DEBUG ya viene de base vía DJANGO_DEBUG

TENANT_STRICT_HOST = True
OAUTH_REQUIRE_EMAIL_VERIFIED = True
OAUTH_ALLOWED_EMAIL_DOMAIN = "*" 
NOTIF_EMAIL_ENABLED = os.getenv("NOTIF_EMAIL_ENABLED", "true").lower() == "true"
AWS_REGION = "us-east-2"                   # tu región SES
NOTIF_EMAIL_FROM = "no-reply@cnd-ia.com"  # remitente verificado en SES
SES_CONFIGURATION_SET = None  