import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger(__name__)

class DebugLoggingMiddleware(MiddlewareMixin):
    """Log request and response details when DEBUG is enabled."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(settings, 'DEBUG_LOG_REQUESTS', settings.DEBUG):
            return None
        request._view_func = view_func
        try:
            payload = request.body.decode('utf-8') if request.body else ''
        except Exception:
            payload = '<unreadable>'
        logger.debug(
            "[REQUEST] %s %s view=%s payload=%s",
            request.method,
            request.get_full_path(),
            view_func.__name__,
            payload,
        )
        return None

    def process_response(self, request, response):
        if getattr(settings, 'DEBUG_LOG_REQUESTS', settings.DEBUG):
            view_name = getattr(getattr(request, '_view_func', None), '__name__', None)
            data = getattr(response, 'data', '<non DRF response>')
            logger.debug(
                "[RESPONSE] %s %s view=%s status=%s data=%s",
                request.method,
                request.get_full_path(),
                view_name,
                getattr(response, 'status_code', 'unknown'),
                data,
            )
        return response
