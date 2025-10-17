from typing import List

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
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
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Filtrar por usuario y cliente actual
        if cliente_actual:
            qs = Notification.objects.filter(recipient=user, cliente_id=cliente_actual.id).order_by("-created_at")
        else:
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
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        # Filtrar por usuario, cliente actual y no leídas
        if cliente_actual:
            cnt = Notification.objects.filter(recipient=request.user, cliente_id=cliente_actual.id, unread=True).count()
        else:
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

        return Response(
            {"id": notif.id, "unread": notif.unread, "read_at": notif.read_at}
        )


class NotificationReadAllView(APIView):
    permission_classes = [InAppPermission]

    def post(self, request):
        qs = Notification.objects.filter(recipient=request.user, unread=True)
        now = timezone.now()
        updated = qs.update(unread=False, read_at=now)
        return Response({"updated": updated})


# ====== NUEVO: borrar individual ======
class NotificationDeleteView(APIView):
    permission_classes = [InAppPermission]

    def delete(self, request, pk):
        deleted, _ = Notification.objects.filter(
            pk=pk, recipient=request.user
        ).delete()
        if deleted == 0:
            return Response({"detail": "Notificación no encontrada"}, status=404)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ====== NUEVO: borrado masivo por IDs ======
class NotificationBulkDeleteView(APIView):
    permission_classes = [InAppPermission]

    def post(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list):
            raise ValidationError({"ids": "Debe ser una lista de enteros."})
        try:
            ids_int: List[int] = [int(x) for x in ids]
        except (TypeError, ValueError):
            raise ValidationError({"ids": "Todos los valores deben ser enteros."})

        qs = Notification.objects.filter(recipient=request.user, id__in=ids_int)
        deleted, _ = qs.delete()
        return Response({"requested": len(ids_int), "deleted": deleted})
