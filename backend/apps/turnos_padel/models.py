from django.db import models
from django.conf import settings
from django.db.models import Q




TIPO_CODIGO_CHOICES = [
    ("x1", "Individual"),
    ("x2", "2 Personas"),
    ("x3", "3 Personas"),
    ("x4", "4 Personas"),
]

class AbonoMes(models.Model):
    ESTADOS = [
        ("pagado", "Pagado"),               # turnos confirmados
        ("vencido", "No pagado a tiempo"),  # prioridad no usada
        ("cancelado", "Cancelado"),         # baja manual
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="abonos_mensuales"
    )
    sede = models.ForeignKey(
        "turnos_core.Lugar",
        on_delete=models.CASCADE,
        related_name="abonos_mensuales"
    )
    prestador = models.ForeignKey(
        "turnos_core.Prestador",
        on_delete=models.CASCADE,
        related_name="abonos_mensuales"
    )
    tipo_clase = models.ForeignKey(
        "turnos_padel.TipoClasePadel",
        on_delete=models.PROTECT,
        related_name="abonos",
        null=True, blank=True,  # ← nullable para abonos personalizados
        help_text="Tipo de clase fijo (para abonos simples). Null si es personalizado."
    )

    tipo_abono = models.ForeignKey(
        "turnos_padel.TipoAbonoPadel",
        on_delete=models.PROTECT,
        related_name="abonos",
        null=True, blank=True,   # ← primera migración suave
    )

    anio = models.IntegerField()
    mes = models.IntegerField()
    dia_semana = models.IntegerField(choices=[
        (0, "Lunes"), (1, "Martes"), (2, "Miércoles"), (3, "Jueves"),
        (4, "Viernes"), (5, "Sábado"), (6, "Domingo")
    ])
    hora = models.TimeField()

    monto = models.DecimalField(max_digits=10, decimal_places=2)
    
    configuracion_personalizada = models.JSONField(
        null=True, 
        blank=True,
        help_text="Configuración personalizada: [{'tipo_clase_id': 1, 'cantidad': 2, 'codigo': 'x1'}, ...]"
    )
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pagado")
    
    renovado = models.BooleanField(
        default=False,
        help_text="Se marca True si fue renovado con un abono del mes siguiente"
    )

    fecha_limite_renovacion = models.DateField(null=True, blank=True)

    turnos_reservados = models.ManyToManyField(
        "turnos_core.Turno",
        blank=True,
        related_name="abonos_confirmados"
    )

    turnos_prioridad = models.ManyToManyField(
        "turnos_core.Turno",
        blank=True,
        related_name="abonos_prioritarios"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sede", "prestador", "anio", "mes", "dia_semana", "hora"],
                condition=models.Q(estado__in=["pagado"]),
                name="uq_abono_mes_franja_pagada"
            )
        ]
        indexes = [
            models.Index(fields=["usuario", "anio", "mes"]),
            models.Index(fields=["sede", "prestador", "anio", "mes"]),
        ]

    def __str__(self):
        return f"AbonoMes {self.usuario_id} {self.anio}-{self.mes:02d} {self.get_dia_semana_display()} {self.hora}"
    
    @property
    def es_personalizado(self):
        """Retorna True si el abono tiene configuración personalizada."""
        return bool(self.configuracion_personalizada)
    
    def get_tipos_clase_configuracion(self):
        """
        Retorna la configuración de tipos de clase.
        Para abonos simples: retorna el tipo_clase único.
        Para abonos personalizados: retorna la configuración JSON.
        """
        if self.es_personalizado:
            return self.configuracion_personalizada
        elif self.tipo_clase:
            return [{
                'tipo_clase_id': self.tipo_clase.id,
                'cantidad': 1,
                'codigo': self.tipo_clase.codigo
            }]
        return []
    
    def calcular_monto_total(self):
        """
        Calcula el monto total basado en la configuración.
        Para abonos simples: usa el precio del tipo_clase.
        Para abonos personalizados: suma precios de cada tipo * cantidad.
        """
        if self.es_personalizado:
            total = 0
            for config in self.configuracion_personalizada:
                try:
                    tipo_clase = TipoClasePadel.objects.get(id=config['tipo_clase_id'])
                    total += float(tipo_clase.precio) * config['cantidad']
                except (TipoClasePadel.DoesNotExist, KeyError, ValueError):
                    continue
            return total
        elif self.tipo_clase:
            return float(self.tipo_clase.precio)
        return 0.0

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
    codigo = models.CharField(max_length=2, choices=TIPO_CODIGO_CHOICES)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["configuracion_sede", "codigo"],
                name="uq_tipo_clase_por_sede_codigo",
            )
        ]

    def __str__(self):
        return f"{self.get_codigo_display()} ({self.configuracion_sede.sede.nombre}) - ${self.precio}"

class TipoAbonoPadel(models.Model):
    configuracion_sede = models.ForeignKey(
        "ConfiguracionSedePadel",
        on_delete=models.CASCADE,
        related_name="tipos_abono"
    )
    codigo = models.CharField(max_length=2, choices=TIPO_CODIGO_CHOICES)
    precio = models.DecimalField(max_digits=10, decimal_places=2)  # precio mensual del abono
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["configuracion_sede", "codigo"],
                name="uq_tipo_abono_por_sede_codigo",
            )
        ]

    def __str__(self):
        return f"{self.get_codigo_display()} - {self.precio}"
