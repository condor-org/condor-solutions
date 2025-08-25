from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
import uuid

class NotificationEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # event_id
    topic = models.CharField(max_length=120, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    cliente_id = models.IntegerField(null=True, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["topic", "created_at"]),
            models.Index(fields=["cliente_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.topic}#{self.id}"


class Notification(models.Model):
    SEVERITY = (("info", "info"), ("warning", "warning"), ("critical", "critical"))

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    event = models.ForeignKey(
        NotificationEvent, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    cliente_id = models.IntegerField(null=True, blank=True, db_index=True)

    type = models.CharField(max_length=40, db_index=True)  # p.ej. CANCELACIONES_TURNOS, RESERVA_TURNO
    severity = models.CharField(max_length=10, choices=SEVERITY, default="info")

    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    deeplink_path = models.CharField(max_length=255, blank=True)
    locale = models.CharField(max_length=10, default="es-AR")

    # target opcional (para ir a un detalle)
    target_ct = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    target_id = models.IntegerField(null=True, blank=True)
    target = GenericForeignKey("target_ct", "target_id")

    unread = models.BooleanField(default=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # idempotencia
    dedupe_key = models.CharField(max_length=255, blank=True, db_index=True)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["recipient", "dedupe_key"], name="uniq_notification_dedupe_per_user")
        ]
        indexes = [
            models.Index(fields=["recipient", "unread", "-created_at"]),
            models.Index(fields=["type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Notif<{self.type}> to {self.recipient_id} {self.title[:40]}"
