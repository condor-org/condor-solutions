#turnos_padel/management/commands/liberar_abonos_vencidos.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.turnos_padel.models import AbonoMes
from apps.turnos_core.models import Turno


class Command(BaseCommand):
    help = "Libera los turnos_prioridad de abonos que no fueron renovados a tiempo"

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        vencidos = AbonoMes.objects.filter(
            estado="pagado",
            fecha_limite_renovacion__lt=hoy
        ).prefetch_related("turnos_prioridad")

        total_abonos = 0
        total_turnos_liberados = 0

        for abono in vencidos:
            # Chequear si hay renovación del mismo abono para el mes siguiente
            abono_siguiente = AbonoMes.objects.filter(
                usuario=abono.usuario,
                sede=abono.sede,
                prestador=abono.prestador,
                dia_semana=abono.dia_semana,
                hora=abono.hora,
                tipo_clase=abono.tipo_clase,
                anio=abono.anio + 1 if abono.mes == 12 else abono.anio,
                mes=1 if abono.mes == 12 else abono.mes + 1,
                estado="pagado"
            ).exists()

            if abono_siguiente:
                continue  # ya fue renovado, no liberar

            with transaction.atomic():
                turnos = abono.turnos_prioridad.select_for_update()
                for turno in turnos:
                    turno.usuario = None
                    turno.estado = "disponible"
                    turno.tipo_turno = None
                    turno.comprobante_abono = None
                    turno.save(update_fields=["usuario", "estado", "tipo_turno", "comprobante_abono"])
                    total_turnos_liberados += 1

                abono.turnos_prioridad.clear()
                abono.estado = "vencido"
                abono.save(update_fields=["estado"])
                total_abonos += 1

        self.stdout.write(self.style.SUCCESS(
            f"Abonos vencidos procesados: {total_abonos} — Turnos liberados: {total_turnos_liberados}"
        ))
