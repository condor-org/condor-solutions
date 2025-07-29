import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class DebugSerializerMixin:
    """Mixin to log create and update operations when DEBUG_LOG_REQUESTS is True."""

    def _log(self, action, data):
        if getattr(settings, 'DEBUG_LOG_REQUESTS', settings.DEBUG):
            logger.debug("[%s %s] data=%s", self.__class__.__name__, action, data)

    def create(self, validated_data):
        self._log('create', validated_data)
        instance = super().create(validated_data)
        self._log('created', getattr(instance, 'id', instance))
        return instance

    def update(self, instance, validated_data):
        self._log('update', validated_data)
        instance = super().update(instance, validated_data)
        self._log('updated', getattr(instance, 'id', instance))
        return instance
