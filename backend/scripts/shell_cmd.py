#!/usr/bin/env python
import os
import django

# ——— Configuración Django ———
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "condor_core.settings.base")
django.setup()

# ——— Imports de tus modelos ———
from apps.turnos_padel.models import Profesor
from apps.turnos_core.models   import Turno
from django.contrib.contenttypes.models import ContentType

# ——— Preparamos el content type de Profesor ———
ct = ContentType.objects.get_for_model(Profesor)

# 1) Listar todos los profesores
profesores = Profesor.objects.all()
print("=== Profesores Registrados ===")
for prof in profesores:
    print(f"- id={prof.id} | nombre={prof.nombre} | email={prof.email or 'sin email'}")
print()

# 2) Para cada profesor, listar sus turnos con detalles
for prof in profesores:
    print(f"=== Turnos de {prof.nombre} (id={prof.id}) ===")
    turnos = Turno.objects.filter(content_type=ct, object_id=prof.id)
    if not turnos.exists():
        print("  (no hay turnos asociados)")
    else:
        for t in turnos:
            usuario = t.usuario.username if t.usuario else "Desconocido"
            email   = t.usuario.email    if t.usuario else "Desconocido"
            print(
                f"  • id={t.id} | fecha={t.fecha} | hora={t.hora} | "
                f"estado={t.estado} | usuario={usuario} ({email}) | sede={t.lugar}"
            )
    print()
