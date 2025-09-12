# condor_core/settings/dev.py
from .base import *
import os
# Dev por ENV (no hardcode)
# DEBUG ya viene de base vía DJANGO_DEBUG
CORS_ALLOW_ALL_ORIGINS = True  # práctico en dev; si querés, controlalo por ENV

OAUTH_AUTO_PROVISION = os.getenv("OAUTH_AUTO_PROVISION", "false").lower() == "true"
OAUTH_ALLOWED_EMAIL_DOMAIN = os.getenv("OAUTH_ALLOWED_EMAIL_DOMAIN", "*")