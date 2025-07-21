# apps/turnos_padel_core/management/commands/generar_turnos.py
from django.core.management.base import BaseCommand
from datetime import datetime
from apps.turnos_padel_core.services.generador import generar_turnos_del_mes


class Command(BaseCommand):
    help = "Genera automáticamente los turnos del mes para todos los profesores con disponibilidad"

    def add_arguments(self, parser):
        parser.add_argument("--anio", type=int, default=datetime.now().year)
        parser.add_argument("--mes", type=int, default=datetime.now().month)
        parser.add_argument("--duracion", type=int, default=60)
        parser.add_argument("--profesor_id", type=int, help="Generar turnos solo para un profesor específico", default=None)

    def handle(self, *args, **options):
        anio = options["anio"]
        mes = options["mes"]
        duracion = options["duracion"]
        profesor_id = options["profesor_id"]

        self.stdout.write(f"📅 Generando turnos para {mes}/{anio} (Duración: {duracion} min)...")

        generar_turnos_del_mes(anio, mes, duracion, profesor_id)

        self.stdout.write(self.style.SUCCESS("✅ Turnos generados correctamente."))
