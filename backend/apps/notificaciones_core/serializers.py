from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "type", "severity", "title", "body", "deeplink_path",
            "unread", "created_at", "metadata"
        ]

class NotificationMarkReadSerializer(serializers.Serializer):
    unread = serializers.BooleanField(required=True)
