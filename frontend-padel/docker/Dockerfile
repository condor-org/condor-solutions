# /frontend-padel/docker/Dockerfile

# Fase de build
FROM node:20.12.2 AS build

WORKDIR /app

# Copiar package.json y dependencias
COPY ../package.json ../package-lock.json ./

RUN npm install

# Copiar el código del proyecto
COPY ../public ./public
COPY ../src ./src

# Copiar el .env del frontend (único para cada cliente)
COPY ../.env ./frontend.env

# Cargar las variables y hacer el build
RUN export $(cat frontend.env | grep -v '^#' | xargs) && \
    npm run build

# Imagen final (servidor Nginx)
FROM nginx:1.25.3-alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
