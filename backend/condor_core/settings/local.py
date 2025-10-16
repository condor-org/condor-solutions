# condor_core/settings/local.py
from .base import *
import os

# Configuración específica para desarrollo local
DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

# ========================================
# DESHABILITAR OAUTH PARA TESTING LOCAL
# ========================================
# Deshabilitamos OAuth para poder probar routing dinámico sin problemas
OAUTH_ENABLED = False
OAUTH_AUTO_PROVISION = False
OAUTH_REQUIRE_EMAIL_VERIFIED = False
OAUTH_ALLOWED_EMAIL_DOMAIN = "*"

# ========================================
# CONFIGURACIÓN MULTI-TENANT
# ========================================
TENANT_STRICT_HOST = False  # Más permisivo en local
TENANT_DEFAULT_CLIENTE_ID = "1"  # Lucas Padel por defecto
TENANT_TRUST_PROXY_HEADERS = True
TENANT_CACHE_TTL_SECONDS = 60  # Cache más corto para testing

# ========================================
# CONFIGURACIÓN DE EMAIL (DESHABILITADA)
# ========================================
NOTIF_EMAIL_ENABLED = False
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ========================================
# CONFIGURACIÓN DE LOGGING
# ========================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'apps.auth_core.views': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
        'condor_core.tenant': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
