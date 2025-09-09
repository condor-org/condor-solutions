# apps/turnos_padel/management/commands/abonos_diario.py
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models import Max

from apps.turnos_padel.models import AbonoMes
from apps.turnos_padel.services.abonos import (
    procesar_renovacion_de_abono,
    liberar_abono_por_vencimiento,
)
from apps.notificaciones_core.services import publish_event, notify_inapp

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Recordatorios in-app de abonos (T-7/T-1) y, pasado el último turno, "
        "aplicar renovación o liberar prioridad."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--hoy",
            type=str,
            default=None,
            help="Simular fecha actual (YYYY-MM-DD). Si no se pasa, usa la fecha local.",
        )
        parser.add_argument(
            "--only",
            type=str,
            choices=["all", "recordatorios", "transiciones"],
            default="all",
            help="Limitar la ejecución a recordatorios o transiciones. Por defecto, all.",
        )

    def handle(self, *args, **kwargs):
        # Permite “viajar en el tiempo” para pruebas
        hoy_arg = kwargs.get("hoy")
        hoy = parse_date(hoy_arg) if hoy_arg else timezone.localdate()

        modo = (kwargs.get("only") or "all").lower()
        solo_recordatorios = modo == "recordatorios"
        solo_transiciones = modo == "transiciones"

        logger.info("[abonos_diario] start hoy=%s modo=%s", hoy, modo)

        # Solo procesamos abonos VIGENTES
        qs = (
            AbonoMes.objects.filter(estado="pagado")
            .select_related("usuario", "sede", "prestador", "tipo_clase")
        )

        total = 0
        rec_t7 = rec_t1 = 0
        trans_renov = trans_lib = 0

        for a in qs:
            try:
                # Último día real del ciclo = último turno reservado del mes
                ult = a.turnos_reservados.aggregate(ultimo=Max("fecha"))["ultimo"]
                if not ult:
                    continue

                dias = (ult - hoy).days

                # --- Recordatorios T-7 / T-1 si aún no renovó ---
                if not solo_transiciones and (not a.renovado and dias in (7, 1)):
                    ev = publish_event(
                        topic="abonos.recordatorio_vencimiento",
                        actor=a.usuario,
                        cliente_id=getattr(a.sede, "cliente_id", None),
                        metadata={"abono_id": a.id, "vence_el": str(ult), "dias": dias},
                    )
                    notify_inapp(
                        event=ev,
                        recipients=[a.usuario],
                        notif_type="abono_recordatorio",
                        context_by_user={
                            a.usuario_id: {
                                "abono_id": a.id,
                                "vence_el": str(ult),
                                "dias": dias,
                                "sede_nombre": getattr(a.sede, "nombre", None),
                            }
                        },
                        severity="warning" if dias == 1 else "info",
                    )
                    if dias == 7:
                        rec_t7 += 1
                    else:
                        rec_t1 += 1

                # --- Día posterior al último turno → transicionar una sola vez ---
                # Guardia idempotente: sólo si todavía hay prioridad para mover/liberar
                if not solo_recordatorios and (hoy > ult and a.turnos_prioridad.exists()):
                    if a.renovado:
                        procesar_renovacion_de_abono(a)
                        ev = publish_event(
                            topic="abonos.renovacion_aplicada",
                            actor=a.usuario,
                            cliente_id=getattr(a.sede, "cliente_id", None),
                            metadata={"abono_id": a.id, "mes": a.mes, "anio": a.anio},
                        )
                        notify_inapp(
                            event=ev,
                            recipients=[a.usuario],
                            notif_type="abono_estado",
                            context_by_user={
                                a.usuario_id: {
                                    "mensaje": "Tu abono fue renovado y aplicado al próximo mes."
                                }
                            },
                            severity="success",
                        )
                        trans_renov += 1
                    else:
                        liberar_abono_por_vencimiento(a)
                        ev = publish_event(
                            topic="abonos.no_renovado",
                            actor=a.usuario,
                            cliente_id=getattr(a.sede, "cliente_id", None),
                            metadata={"abono_id": a.id, "mes": a.mes, "anio": a.anio},
                        )
                        notify_inapp(
                            event=ev,
                            recipients=[a.usuario],
                            notif_type="abono_estado",
                            context_by_user={
                                a.usuario_id: {
                                    "mensaje": "Tu abono venció y se liberó la prioridad."
                                }
                            },
                            severity="info",
                        )
                        trans_lib += 1

                total += 1

            except Exception:
                logger.exception("[abonos_diario] Error procesando abono %s", a.id)

        logger.info(
            "[abonos_diario] done hoy=%s modo=%s abonos=%s rec_T-7=%s rec_T-1=%s "
            "trans_renov=%s trans_lib=%s",
            hoy, modo, total, rec_t7, rec_t1, trans_renov, trans_lib
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"OK hoy={hoy} modo={modo} | abonos={total} | rec_T-7={rec_t7} rec_T-1={rec_t1} "
                f"| renovados={trans_renov} liberados={trans_lib}"
            )
        )
