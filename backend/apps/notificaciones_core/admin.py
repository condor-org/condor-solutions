from django.contrib import admin
from .models import NotificationEvent, Notification

@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "cliente_id", "created_at")
    search_fields = ("id", "topic")
    list_filter = ("topic", "cliente_id")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "type", "unread", "created_at")
    list_filter = ("type", "unread")
    search_fields = ("title", "recipient__email", "recipient__username")
