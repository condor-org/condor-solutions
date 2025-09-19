#!/bin/sh
set -eu

case "${PROXY_MODE:-local}" in
  local) cp /etc/nginx/nginx.local.conf /etc/nginx/nginx.conf ;;
  ec2)   cp /etc/nginx/nginx.ec2.conf   /etc/nginx/nginx.conf ;;
  *)     echo "PROXY_MODE inválido: ${PROXY_MODE}" >&2; exit 1 ;;
esac

nginx -t
echo "[proxy] PROXY_MODE=${PROXY_MODE}"
exec nginx -g 'daemon off;'