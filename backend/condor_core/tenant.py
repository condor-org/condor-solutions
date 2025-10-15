# apps/common/middleware/tenant.py
import os
import logging
import idna
from django.http import JsonResponse
from django.core.cache import cache
from apps.clientes_core.models import Cliente, ClienteDominio

log = logging.getLogger(__name__)

class TenantMiddleware:
    """
    - Resuelve request.cliente_actual a partir del Host (confiando en el reverse proxy).
    - Si TENANT_STRICT_HOST=True y el host no está mapeado, request.cliente_actual=None (se loguea).
    - En requests autenticadas (no super_admin), exige match user.cliente == cliente_actual (403).
    - Cachea el mapeo hostname → cliente_id para reducir hits a DB.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.strict = os.getenv("TENANT_STRICT_HOST", "True") == "True"
        self.default_cliente_id = os.getenv("TENANT_DEFAULT_CLIENTE_ID")  # solo si strict=False
        self.trust_proxy = os.getenv("TENANT_TRUST_PROXY_HEADERS", "True") == "True"
        self.cache_ttl = int(os.getenv("TENANT_CACHE_TTL_SECONDS", "300"))  # 5 min por defecto

    def _normalize_host(self, host: str) -> str:
        """
        Normaliza: lower, sin puerto, punycode → unicode seguro, sin espacios.
        """
        if not host:
            return ""
        host = host.split(":")[0].strip().lower()
        try:
            # soporta IDN (por si acaso)
            host = idna.decode(idna.encode(host))
        except Exception:
            pass
        return host

    def _get_request_host(self, request) -> str:
        """
        Toma el host desde el header del proxy si está habilitado (confiable),
        si no, cae a request.get_host().
        """
        if self.trust_proxy:
            host = request.META.get("HTTP_X_TENANT_HOST") or request.META.get("HTTP_HOST")
            if host:
                return self._normalize_host(host)
        return self._normalize_host(request.get_host())

    def _resolve_cliente(self, host: str):
        """
        Resuelve cliente por host con cache.
        Devuelve instancia de Cliente o None.
        """
        if not host:
            return None

        cache_key = f"tenant:host:{host}"
        cached = cache.get(cache_key)
        if cached is not None:
            # cached puede ser cliente_id (int) o -1 para “no encontrado”
            if cached == -1:
                return None
            try:
                return Cliente.objects.only("id").get(id=cached)
            except Cliente.DoesNotExist:
                # Evitar bucle si alguien borró cliente: invalidar y seguir a DB
                cache.delete(cache_key)

        try:
            dom = (
                ClienteDominio.objects
                .select_related("cliente")
                .only("id", "hostname", "activo", "cliente__id")
                .get(hostname=host, activo=True)
            )
            cliente_id = dom.cliente_id
            cache.set(cache_key, cliente_id, self.cache_ttl)
            return dom.cliente
        except ClienteDominio.DoesNotExist:
            cache.set(cache_key, -1, self.cache_ttl)  # negativo para cachear “no existe”
            return None

    def __call__(self, request):
        host = self._get_request_host(request)
        log.info("[TENANT] request_host=%s X-Tenant-Host=%s HTTP_HOST=%s PATH=%s METHOD=%s USER_AGENT=%s", 
                host, 
                request.META.get("HTTP_X_TENANT_HOST", "N/A"),
                request.META.get("HTTP_HOST", "N/A"),
                request.path,
                request.method,
                request.META.get("HTTP_USER_AGENT", "N/A")[:100])
        cliente = self._resolve_cliente(host)
        
        # ✅ LOG: Cliente detectado
        log.info("[TENANT] cliente_detectado=%s host=%s", 
                cliente.nombre if cliente else "None", host)

        if not cliente:
            if not self.strict and self.default_cliente_id:
                cliente = Cliente.objects.filter(id=self.default_cliente_id).only("id").first()
                if cliente:
                    log.warning("[TENANT] host_no_mapeado strict=False usando_default host=%s cliente_id=%s", host, cliente.id)
            else:
                # strict → dejamos None y logueamos (no cortamos si no está autenticado)
                log.info("[TENANT] host_desconocido host=%s", host)

        request.cliente_actual = cliente

        # Enforce solo si el usuario ya está autenticado
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            # super_admin pasa siempre
            if getattr(user, "tipo_usuario", "") != "super_admin":
                u_cli = getattr(user, "cliente_id", None)
                c_id = getattr(cliente, "id", None)
                if not cliente or u_cli != c_id:
                    log.info(
                        "[TENANT ENFORCE] mismatch user_id=%s user_cliente=%s ctx_cliente=%s path=%s host=%s",
                        getattr(user, "id", None), u_cli, c_id, request.path, host
                    )
                    return JsonResponse({"detail": "tenant_mismatch"}, status=403)

        return self.get_response(request)
