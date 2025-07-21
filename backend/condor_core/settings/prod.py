from .base import *

DEBUG = False

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')

import dj_database_url

DATABASES = {
    "default": dj_database_url.config(default=os.environ.get('DATABASE_URL'))
}

CORS_ALLOWED_ORIGINS = [
    "https://miapp.com",
    "https://www.miapp.com",
]