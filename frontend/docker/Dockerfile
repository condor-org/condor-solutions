# /frontend/docker/Dockerfile

# Fase de build
FROM node:20 AS build

WORKDIR /app

# Recibe variables desde docker-compose
ARG REACT_APP_API_BASE_URL
ENV REACT_APP_API_BASE_URL=$REACT_APP_API_BASE_URL

COPY ../package.json ../package-lock.json ./
RUN npm install

COPY ../public ./public
COPY ../src ./src

# Construye el frontend usando la variable ya cargada
RUN npm run build

# Imagen final
FROM nginx:stable-alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
