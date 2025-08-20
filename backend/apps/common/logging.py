import logging
from rest_framework import serializers


class LoggedModelSerializer(serializers.ModelSerializer):
    """ModelSerializer que registra create y update."""

    def create(self, validated_data):
        """Create a model instance logging the input data.

        Args:
            validated_data (dict): Data validated by the serializer.

        Returns:
            Model: The newly created model instance.
        """
        logger = logging.getLogger(self.__class__.__name__)
        logger.info("create called with data=%s", validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update a model instance logging the new data.

        Args:
            instance (Model): Existing model instance to update.
            validated_data (dict): Data validated by the serializer.

        Returns:
            Model: The updated model instance.
        """
        logger = logging.getLogger(self.__class__.__name__)
        logger.info("update called with data=%s", validated_data)
        return super().update(instance, validated_data)
