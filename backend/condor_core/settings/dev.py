# condor_core/settings/dev.py
from .base import *

# Dev por ENV (no hardcode)
# DEBUG ya viene de base vía DJANGO_DEBUG
CORS_ALLOW_ALL_ORIGINS = True  # práctico en dev; si querés, controlalo por ENV
