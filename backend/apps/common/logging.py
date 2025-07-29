import logging
from rest_framework import serializers


class LoggedModelSerializer(serializers.ModelSerializer):
    """ModelSerializer que registra create y update."""

    def create(self, validated_data):
        logger = logging.getLogger(self.__class__.__name__)
        logger.info("create called with data=%s", validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        logger = logging.getLogger(self.__class__.__name__)
        logger.info("update called with data=%s", validated_data)
        return super().update(instance, validated_data)
