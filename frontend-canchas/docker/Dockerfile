# frontend-padel/docker/Dockerfile

FROM node:20.12.2 AS build
WORKDIR /app

# Instalar deps (cacheables)
COPY frontend-canchas/package*.json ./
RUN npm ci --no-audit --no-fund

# Copiar shared-auth ANTES del frontend para evitar conflictos
COPY shared-auth/src ./src/shared-auth

# Build (sin hornear envs)
COPY frontend-canchas/ ./

RUN npm run build

# ──────────────────────────────────────────────────────────

FROM nginx:1.25.3-alpine

# Logs a stdout/err
RUN sed -i 's#access_log .*#access_log /dev/stdout;#' /etc/nginx/nginx.conf \
 && sed -i 's#error_log .*#error_log /dev/stderr warn;#' /etc/nginx/nginx.conf

# Nginx del frontend (SPA + cache assets)
COPY frontend-canchas/docker/nginx.conf /etc/nginx/conf.d/default.conf

# App estática
COPY --from=build /app/build /usr/share/nginx/html

# Placeholder para evitar 404 si no hay envs
RUN echo "window.RUNTIME_CONFIG={};" > /usr/share/nginx/html/config.js

# EntryPoint: genera config.js con PUBLIC_* en runtime
COPY frontend-canchas/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx","-g","daemon off;"]
