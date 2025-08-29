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
USER app

EXPOSE 8000

# Logs a stdout/err; nivel overrideable por DJANGO_LOG_LEVEL
CMD ["gunicorn","condor_core.wsgi:application","--bind","0.0.0.0:8000","--access-logfile","-","--error-logfile","-","--log-level","info"]
