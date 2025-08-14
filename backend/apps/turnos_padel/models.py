from django.db import models
from django.conf import settings
from django.db.models import Q

class AbonoMes(models.Model):
    ESTADOS = [
        ("creado", "Creado"),        # creado por admin, aún sin reserva
        ("pagado", "Pagado"),        # reservado (con o sin comprobante, según TB usados)
        ("vencido", "Vencido"),      # no pagado a tiempo (se libera)
        ("cancelado", "Cancelado"),  # baja manual
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="abonos_mensuales"
    )
    sede = models.ForeignKey(
        "turnos_core.Lugar",                   # ← referencia perezosa por string
        on_delete=models.CASCADE,
        related_name="abonos_mensuales"
    )
    prestador = models.ForeignKey(
        "turnos_core.Prestador",               # ← referencia perezosa por string
        on_delete=models.CASCADE,
        related_name="abonos_mensuales"
    )

    anio = models.IntegerField()
    mes = models.IntegerField()  # 1..12
    dia_semana = models.IntegerField(choices=[
        (0, "Lunes"), (1, "Martes"), (2, "Miércoles"), (3, "Jueves"),
        (4, "Viernes"), (5, "Sábado"), (6, "Domingo")
    ])
    hora = models.TimeField()

    tipo_clase = models.ForeignKey(
        "turnos_padel.TipoClasePadel",        # ← referencia perezosa por string
        on_delete=models.PROTECT,
        related_name="abonos"
    )  # debe ser de esta sede
    monto = models.DecimalField(max_digits=10, decimal_places=2)  # TOTAL del mes (puede incluir descuento)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="creado")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        # Unicidad de franja para abonos activos (prioridad real)
        constraints = [
            models.UniqueConstraint(
                fields=["sede", "prestador", "anio", "mes", "dia_semana", "hora"],
                condition=Q(estado__in=["creado", "pagado"]),
                name="uq_abono_mes_franja_activa"
            )
        ]
        indexes = [
            models.Index(fields=["usuario", "anio", "mes"]),
            models.Index(fields=["sede", "prestador", "anio", "mes"]),
        ]

    def __str__(self):
        return f"AbonoMes {self.usuario_id} {self.anio}-{self.mes:02d} {self.get_dia_semana_display()} {self.hora}"


class ConfiguracionSedePadel(models.Model):
    sede = models.OneToOneField(
        "turnos_core.Lugar",
        on_delete=models.CASCADE,
        related_name="configuracion_padel"
    )
    alias = models.CharField(max_length=100, blank=True)
    cbu_cvu = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"Config {self.sede.nombre}"


class TipoClasePadel(models.Model):
    configuracion_sede = models.ForeignKey(
        "turnos_padel.ConfiguracionSedePadel",   # ← referencia perezosa por string
        on_delete=models.CASCADE,
        related_name="tipos_clase"
    )
    nombre = models.CharField(max_length=50)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nombre} ({self.configuracion_sede.sede.nombre}) - ${self.precio}"
