# settings/dev.py

from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'condor_db',
        'USER': 'condor_user',
        'PASSWORD': 'condor_password',
        'HOST': 'db',  # Este es el nombre del servicio definido en docker-compose.yml
        'PORT': '5432',
    }
}

CORS_ALLOW_ALL_ORIGINS = True
