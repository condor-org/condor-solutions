# apps/pagos_core/management/commands/liberar_turnos_vencidos.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.pagos_core.models import PagoIntento
from apps.turnos_core.models import Turno

class Command(BaseCommand):
    help = "Libera turnos con pagos vencidos"

    def handle(self, *args, **options):
        now = timezone.now()
        vencidos = PagoIntento.objects.filter(
            estado='pendiente',
            tiempo_expiracion__lt=now
        )
        total = vencidos.count()

        for pago in vencidos:
            turno = Turno.objects.filter(pk=pago.object_id).first()
            if turno and turno.usuario:
                turno.usuario = None
                turno.estado = 'pendiente'
                turno.save()
            pago.estado = 'vencido'
            pago.save()

        self.stdout.write(self.style.SUCCESS(f'Turnos liberados: {total}'))
