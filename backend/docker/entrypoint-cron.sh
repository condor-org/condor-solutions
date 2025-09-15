#!/bin/sh
set -e

# Exportá a /etc/environment las variables que necesitás en los jobs
# (ajustá el grep si tenés otras)
( env | grep -E '^(DATABASE_URL|DB_|POSTGRES_|DJANGO_|SECRET_|EMAIL_|REDIS_|AWS_|SENTRY_)' || true ) > /etc/environment

# Aplicá migraciones (idempotente). Así evitás el “no such table …”
python manage.py migrate --noinput

# Lanzá cron en foreground con logs a stdout del contenedor
exec cron -f -L 15