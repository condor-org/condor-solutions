# apps/notificaciones_core/urls.py
from django.urls import path
from .views import (
    NotificationListView,
    NotificationUnreadCountView,
    NotificationMarkReadView,
    NotificationReadAllView,
)

urlpatterns = [
    # Listado (con paginación limit/offset del backend)
    # GET /api/notificaciones/
    path("", NotificationListView.as_view(), name="notificaciones-list"),

    # Contador de no leídas
    # GET /api/notificaciones/unread_count/
    path("unread_count/", NotificationUnreadCountView.as_view(), name="notificaciones-unread-count"),

    # Marcar una notificación como (no) leída
    # PATCH /api/notificaciones/<id>/read/
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="notificaciones-mark-read"),

    # Marcar todas como leídas
    # POST /api/notificaciones/read_all/
    path("read_all/", NotificationReadAllView.as_view(), name="notificaciones-read-all"),
]
