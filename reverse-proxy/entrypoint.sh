#!/bin/sh
set -eu

case "${PROXY_MODE:-local}" in
  local) 
    cp /etc/nginx/nginx.local.conf /etc/nginx/nginx.conf 
    echo "[proxy] Usando configuración LOCAL"
    ;;
  ec2)   
    if [ "${ENVIRONMENT:-prod}" = "dev" ]; then
      echo "[proxy] Usando configuración DEV"
      cp /etc/nginx/nginx.ec2.dev.conf /etc/nginx/nginx.conf
    else
      echo "[proxy] Usando configuración PROD"
      cp /etc/nginx/nginx.ec2.prod.conf /etc/nginx/nginx.conf
    fi
    ;;
  *)     
    echo "PROXY_MODE inválido: ${PROXY_MODE}" >&2; exit 1 
    ;;
esac

nginx -t
echo "[proxy] PROXY_MODE=${PROXY_MODE}, ENVIRONMENT=${ENVIRONMENT:-prod}"
exec nginx -g 'daemon off;'