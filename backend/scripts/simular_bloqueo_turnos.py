# backend/scripts/simular_bloqueo_turnos.py

#!/usr/bin/env python
import os
import django

# — Django setup —
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "condor_core.settings.base")
django.setup()

from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.models      import Turno, BloqueoTurnos

def simulate_eliminar_turnos(bloqueo_id):
    bloqueo = BloqueoTurnos.objects.get(id=bloqueo_id)
    filtros = {
        "content_type": bloqueo.content_type,
        "object_id":    bloqueo.object_id,
        "fecha__gte":   bloqueo.fecha_inicio,
        "fecha__lte":   bloqueo.fecha_fin,
    }
    if bloqueo.lugar is not None:
        filtros["lugar"] = bloqueo.lugar

    print(f"\n=== Simulación para bloqueo {bloqueo_id} ===")
    print("Filtros:", filtros)

    qs = Turno.objects.filter(**filtros)
    print("Total en rango:", qs.count())
    print("  – Disponibles antes:", qs.filter(estado="disponible").count())
    qs.filter(estado="disponible").update(estado="cancelado")
    print("  – Reservados sin tocar:", qs.filter(estado="reservado").count())

    reporte = [{
        "id":    t.id,
        "fecha": t.fecha.strftime("%Y-%m-%d"),
        "hora":  t.hora.strftime("%H:%M"),
    } for t in qs.filter(estado="reservado")]

    print("Reporte:", reporte)
    return reporte

# — LLAMADAS directas al final, SIN guard —
simulate_eliminar_turnos(10)
simulate_eliminar_turnos(11)
