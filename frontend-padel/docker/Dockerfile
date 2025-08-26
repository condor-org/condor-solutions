# /frontend-padel/docker/Dockerfile
FROM node:20.12.2 AS build
WORKDIR /app

# deps (cacheables)
COPY ../package*.json ./
RUN npm ci --no-audit --no-fund

# código + .env.* (CRA los lee solo)
COPY ../ ./
ARG REACT_ENV=production
RUN set -e; \
    cp -f .env.${REACT_ENV} .env 2>/dev/null || true; \
    rm -f .env.development .env.production .env.local .env.*.local || true; \
    npm run build

FROM nginx:1.25.3-alpine
# logs a stdout/err
RUN sed -i 's#access_log .*#access_log /dev/stdout;#' /etc/nginx/nginx.conf \
 && sed -i 's#error_log .*#error_log /dev/stderr warn;#' /etc/nginx/nginx.conf
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx","-g","daemon off;"]

