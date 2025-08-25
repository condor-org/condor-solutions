# apps/notificaciones_core/urls.py
from django.urls import path
from .views import (
    NotificationListView,
    NotificationUnreadCountView,
    NotificationMarkReadView,
    NotificationReadAllView,
    NotificationDeleteView,
    NotificationBulkDeleteView,
)

urlpatterns = [
    # Listado (paginado limit/offset)
    # GET /api/notificaciones/
    path("", NotificationListView.as_view(), name="notificaciones-list"),

    # Contador de no leídas
    # GET /api/notificaciones/unread_count/
    path("unread_count/", NotificationUnreadCountView.as_view(), name="notificaciones-unread-count"),

    # Marcar todas como leídas
    # POST /api/notificaciones/read_all/
    path("read_all/", NotificationReadAllView.as_view(), name="notificaciones-read-all"),

    # Borrado masivo
    # POST /api/notificaciones/bulk_delete/  body: {"ids":[1,2,3]}
    path("bulk_delete/", NotificationBulkDeleteView.as_view(), name="notificaciones-bulk-delete"),

    # Marcar (no) leída una notificación
    # PATCH /api/notificaciones/<id>/read/
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="notificaciones-mark-read"),

    # Borrar una notificación
    # DELETE /api/notificaciones/<id>/
    path("<int:pk>/", NotificationDeleteView.as_view(), name="notificaciones-delete"),
]
