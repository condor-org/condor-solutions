from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from .models import BloqueoTurnos

def esta_bloqueado(recurso, lugar, fecha):
    ct = ContentType.objects.get_for_model(recurso.__class__)
    return BloqueoTurnos.objects.filter(
        content_type=ct,
        object_id=recurso.id,
        activo=True,
        fecha_inicio__lte=fecha,
        fecha_fin__gte=fecha
    ).filter(
        Q(lugar=lugar) | Q(lugar__isnull=True)
    ).exists()
