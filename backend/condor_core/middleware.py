import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class LoggingMiddleware(MiddlewareMixin):
    """Log each request and response."""

    def process_request(self, request):
        logger.info(
            "Request: %s %s from %s", request.method, request.get_full_path(), request.META.get("REMOTE_ADDR")
        )

    def process_response(self, request, response):
        logger.info(
            "Response: %s %s %s", request.method, request.get_full_path(), response.status_code
        )
        return response
