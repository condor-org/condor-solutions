from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from .models import Notification
from .serializers import NotificationSerializer, NotificationMarkReadSerializer

class InAppPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [InAppPermission]

    def get_queryset(self):
        user = self.request.user
        qs = Notification.objects.filter(recipient=user).order_by("-created_at")
        unread = self.request.query_params.get("unread")
        notif_type = self.request.query_params.get("type")
        if unread in {"1", "true", "True"}:
            qs = qs.filter(unread=True)
        if notif_type:
            qs = qs.filter(type=notif_type)
        return qs

class NotificationUnreadCountView(APIView):
    permission_classes = [InAppPermission]
    def get(self, request):
        cnt = Notification.objects.filter(recipient=request.user, unread=True).count()
        return Response({"unread_count": cnt})

class NotificationMarkReadView(APIView):
    permission_classes = [InAppPermission]
    def patch(self, request, pk):
        notif = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if not notif:
            return Response({"detail": "Notificación no encontrada"}, status=404)
        ser = NotificationMarkReadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        unread = ser.validated_data["unread"]
        if unread is False and notif.unread:
            notif.unread = False
            notif.read_at = timezone.now()
            notif.save(update_fields=["unread", "read_at"])
        elif unread is True and not notif.unread:
            notif.unread = True
            notif.read_at = None
            notif.save(update_fields=["unread", "read_at"])
        return Response({"id": notif.id, "unread": notif.unread, "read_at": notif.read_at})

class NotificationReadAllView(APIView):
    permission_classes = [InAppPermission]
    def post(self, request):
        qs = Notification.objects.filter(recipient=request.user, unread=True)
        now = timezone.now()
        updated = qs.update(unread=False, read_at=now)
        return Response({"updated": updated})
