# /backend/docker/Dockerfile
FROM python:3.11.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Ajustable en runtime (compose): workers/timeouts sin tocar la imagen
    GUNICORN_CMD_ARGS="--workers=2 --threads=1 --timeout=60 --graceful-timeout=30 --preload"

# Deps del sistema (psycopg/compilación). Dejá tesseract solo si lo usás.
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential gcc libpq-dev tesseract-ocr \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Capas cacheables
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Código
COPY . .

# Usuario no-root para runtime
RUN useradd -m -u 10001 app && chown -R app:app /app
# Asegurar permisos del directorio media (se ejecuta como root durante build)
RUN mkdir -p /app/media && chown -R app:app /app/media

# Copiar y configurar entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER app

EXPOSE 8000

# Usar entrypoint que ejecuta migraciones automáticamente
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn","condor_core.wsgi:application","--bind","0.0.0.0:8000","--access-logfile","-","--error-logfile","-","--log-level","info"]
