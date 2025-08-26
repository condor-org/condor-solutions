# condor_core/settings/base.py

from pathlib import Path
from datetime import timedelta
import os
import logging
from urllib.parse import urlparse

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------------------------------------------------
# Core
# -------------------------------------------------------------------
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-unsafe-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# -------------------------------------------------------------------
# Apps
# -------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
]
THIRD_PARTY_APPS = [
    'django_filters', 'rest_framework', 'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist', 'corsheaders',
]
PROJECT_APPS = [
    'apps.turnos_core', 'apps.pagos_core', 'apps.auth_core',
    'apps.clientes_core', 'apps.turnos_padel', 'apps.common', 'apps.notificaciones_core',
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

# -------------------------------------------------------------------
# Middleware
# -------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'condor_core.middleware.LoggingMiddleware',  # tu middleware
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -------------------------------------------------------------------
# URLs & WSGI
# -------------------------------------------------------------------
ROOT_URLCONF = 'condor_core.urls'
WSGI_APPLICATION = 'condor_core.wsgi.application'

# -------------------------------------------------------------------
# Templates
# -------------------------------------------------------------------
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [os.path.join(BASE_DIR, '..', 'templates')],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

# -------------------------------------------------------------------
# Database (DATABASE_URL > POSTGRES_* > sqlite)
# -------------------------------------------------------------------
def _db_from_env():
    url = os.getenv('DATABASE_URL', '').strip()
    if url:
        u = urlparse(url)
        engine = {
            'postgres': 'django.db.backends.postgresql',
            'postgresql': 'django.db.backends.postgresql',
            'postgresql_psycopg2': 'django.db.backends.postgresql',
            'mysql': 'django.db.backends.mysql',
            'sqlite': 'django.db.backends.sqlite3',
        }.get(u.scheme, 'django.db.backends.postgresql')
        name = u.path.lstrip('/') or str(BASE_DIR / '../db.sqlite3')
        return {
            'ENGINE': engine, 'NAME': name,
            'USER': u.username or '', 'PASSWORD': u.password or '',
            'HOST': u.hostname or '', 'PORT': u.port or '',
            'OPTIONS': {'sslmode': 'require'} if engine.endswith('postgresql') and os.getenv('DB_SSLMODE_REQUIRE', 'True') == 'True' else {},
        }

    # Fallback POSTGRES_*
    if os.getenv('POSTGRES_DB'):
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB'),
            'USER': os.getenv('POSTGRES_USER', ''),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
            'OPTIONS': {'sslmode': 'disable'} if os.getenv('DB_SSLMODE_REQUIRE', 'True') != 'True' else {},
        }

    # Dev sqlite
    return {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / '../db.sqlite3'}

DATABASES = {'default': _db_from_env()}

# -------------------------------------------------------------------
# Auth
# -------------------------------------------------------------------
AUTH_USER_MODEL = 'auth_core.Usuario'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -------------------------------------------------------------------
# I18N / TZ
# -------------------------------------------------------------------
LANGUAGE_CODE = os.getenv('DJANGO_LANG', 'es')
TIME_ZONE = os.getenv('DJANGO_TZ', 'America/Argentina/Buenos_Aires')
USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------------
# Static & Media
# -------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.getenv('DJANGO_STATIC_ROOT', str(BASE_DIR / '../staticfiles'))
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.getenv('DJANGO_MEDIA_ROOT', str(BASE_DIR / '../media'))

# -------------------------------------------------------------------
# DRF / JWT
# -------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework_simplejwt.authentication.JWTAuthentication',),
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': int(os.getenv('DJANGO_PAGE_SIZE', '10')),
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', '30'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '7'))),
    'BLACKLIST_AFTER_ROTATION': True,
    'ROTATE_REFRESH_TOKENS': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# -------------------------------------------------------------------
# Swagger
# -------------------------------------------------------------------
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {'type': 'apiKey', 'name': 'Authorization', 'in': 'header',
                   'description': 'JWT Authorization header using the Bearer scheme.'}
    }
}

# -------------------------------------------------------------------
# Logging (stdout; filtros para bajar ruido por ENV)
# -------------------------------------------------------------------
class MessageDenylistFilter(logging.Filter):
    """Filtra registros cuyo mensaje contenga alguno de los substrings en DJANGO_LOG_SKIP_CONTAINS (csv)."""
    def __init__(self, denylist=None):
        super().__init__()
        self.denylist = [s.strip() for s in (denylist or []) if s and s.strip()]

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        for sub in self.denylist:
            if sub and sub in msg:
                return False
        return True

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("DJANGO_LOG_FORMAT", "text")  # text|json
REQUEST_LOG_LEVEL = os.getenv("DJANGO_REQUEST_LOG_LEVEL", "WARNING")  # WARNING|ERROR
MIDDLEWARE_LOG_LEVEL = os.getenv("DJANGO_MIDDLEWARE_LOG_LEVEL", "WARNING")
_skip = [s for s in os.getenv("DJANGO_LOG_SKIP_CONTAINS", "").split(",") if s]

_formatters = {
    "text": {"format": "[{levelname}] {asctime} {name} {message}", "style": "{"},
    "json": {"()": "pythonjsonlogger.jsonlogger.JsonFormatter",
             "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s"},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"denylist": {"()": MessageDenylistFilter, "denylist": _skip}},
    "formatters": {"app": _formatters["json"] if LOG_FORMAT == "json" else _formatters["text"]},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "app", "filters": ["denylist"]}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        # baja ruido de Django request (p.ej. Unauthorized)
        "django.request": {"handlers": ["console"], "level": REQUEST_LOG_LEVEL, "propagate": False},
        # baja ruido del middleware propio (Request/Response spam)
        "condor_core.middleware": {"handlers": ["console"], "level": MIDDLEWARE_LOG_LEVEL, "propagate": False},
        # gunicorn
        "gunicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "gunicorn.access": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        # módulos de negocio
        "apps": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
