from django.urls import path
from .views import (
    NotificationListView,
    NotificationUnreadCountView,
    NotificationMarkReadView,
    NotificationReadAllView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications-list"),
    path("unread_count/", NotificationUnreadCountView.as_view(), name="notifications-unread-count"),
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="notifications-mark-read"),
    path("read_all/", NotificationReadAllView.as_view(), name="notifications-read-all"),
]
