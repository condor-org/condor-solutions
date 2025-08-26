# condor_core/settings/prod.py
from .base import *
import os

DEBUG = False

# Seguridad básica en prod (activable por ENV)
SECURE_SSL_REDIRECT = os.getenv('DJANGO_SSL_REDIRECT', 'True') == 'True'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_HSTS_SECONDS', '0'))  # subilo a 31536000 cuando tengas TLS estable
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('DJANGO_HSTS_INCLUDE_SUBDOMAINS', 'False') == 'True'
SECURE_HSTS_PRELOAD = os.getenv('DJANGO_HSTS_PRELOAD', 'False') == 'True'

# En prod exigimos DB real
if not os.getenv('DATABASE_URL') and not os.getenv('POSTGRES_DB'):
    raise RuntimeError("Configura DATABASE_URL o variables POSTGRES_* en producción.")

# Por defecto logs JSON en prod (si no definiste DJANGO_LOG_FORMAT)
if 'DJANGO_LOG_FORMAT' not in os.environ:
    os.environ['DJANGO_LOG_FORMAT'] = 'json'


SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO","https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT","True") == "True"
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS","").split(",")