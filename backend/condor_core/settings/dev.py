from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Base de datos local (sqlite)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "../db.sqlite3",
    }
}

CORS_ALLOW_ALL_ORIGINS = True