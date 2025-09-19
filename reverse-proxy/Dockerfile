FROM nginx:1.25-alpine

# Copiamos ambas confs con nombres nuevos
COPY nginx.local.conf /etc/nginx/nginx.local.conf
COPY nginx.ec2.conf   /etc/nginx/nginx.ec2.conf

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default para LOCAL
ENV PROXY_MODE=local

EXPOSE 8080 8443
HEALTHCHECK --interval=30s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
CMD ["/entrypoint.sh"]