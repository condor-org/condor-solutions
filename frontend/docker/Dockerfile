# Dockerfile - Frontend (CRA)

FROM node:20 AS build

WORKDIR /app

# Copiar el .env en el contexto del build (importantísimo)
COPY ../.env .env

COPY ../package.json ../package-lock.json ./
RUN npm install

COPY ../public ./public
COPY ../src ./src

RUN npm run build

FROM nginx:stable-alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]