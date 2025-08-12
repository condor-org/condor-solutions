from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from .models import BloqueoTurnos
from datetime import datetime, timedelta
from django.utils.timezone import make_aware

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


def cumple_politica_cancelacion(turno):
    """
    Retorna True si el turno puede ser cancelado según política.
    Por ahora: al menos 6 horas de anticipación.
    """
    ahora = make_aware(datetime.now())
    dt_turno = make_aware(datetime.combine(turno.fecha, turno.hora))
    return dt_turno - ahora >= timedelta(hours=6)
