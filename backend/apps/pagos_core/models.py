# condor/apps/pagos_core/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.models import Turno
from pathlib import Path

User = get_user_model()


class PagoIntento(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("pre_aprobado", "Preaprobado"),
        ("rechazado", "Rechazado"),
        ("confirmado", "Confirmado"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    creado_en = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    monto_esperado = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=10, default="ARS")

    alias_destino = models.CharField(max_length=100)
    cbu_destino = models.CharField(max_length=64, blank=True, null=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    origen = GenericForeignKey("content_type", "object_id")

    tiempo_expiracion = models.DateTimeField()

    external_reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    id_transaccion_banco = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Pago de {self.usuario} - {self.estado}"


def comprobante_upload_path(instance, filename):
    # Guarda como media/comprobantes/turno_45/archivo.pdf
    return f"comprobantes/turno_{instance.turno.id}/{filename}"

class ComprobantePago(models.Model):
    turno = models.OneToOneField(
        Turno,
        on_delete=models.CASCADE,
        related_name="comprobante",
        null=True,      # ← permitir migrar sin datos previos
        blank=True,
    )
    archivo = models.FileField(upload_to=comprobante_upload_path)
    hash_archivo = models.CharField(max_length=64, unique=True)
    valido = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    datos_extraidos = models.JSONField(blank=True, null=True)
    nro_operacion = models.CharField(max_length=100, blank=True, null=True)
    emisor_nombre = models.CharField(max_length=255, blank=True, null=True)
    emisor_cbu = models.CharField(max_length=22, blank=True, null=True)
    emisor_cuit = models.CharField(max_length=20, blank=True, null=True)
    fecha_detectada = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Comprobante de pago"
        verbose_name_plural = "Comprobantes de pago"
        ordering = ("-created_at",)

    def __str__(self):
        return f"Comprobante #{self.pk} – Turno {self.turno_id}"



class ConfiguracionPago(models.Model):
    destinatario = models.CharField(max_length=255)  # Ej: "Padel Club SRL"
    cbu = models.CharField(max_length=22)
    alias = models.CharField(max_length=100, blank=True)
    monto_esperado = models.DecimalField(max_digits=10, decimal_places=2)
    tiempo_maximo_minutos = models.IntegerField(default=60)

    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CBU: {self.cbu} – Monto esperado: {self.monto_esperado}"
