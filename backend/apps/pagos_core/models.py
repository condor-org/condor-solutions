# condor/apps/pagos_core/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from pathlib import Path
from apps.clientes_core.models import Cliente
from django.utils import timezone

User = get_user_model()

def comprobante_abono_upload_path(instance, filename):
    return f"comprobantes/abono_mes_{instance.abono_mes_id}/{filename}"

class ComprobanteAbono(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="comprobantes_abono")
    abono_mes = models.OneToOneField("turnos_padel.AbonoMes", on_delete=models.CASCADE, related_name="comprobante")
    archivo = models.FileField(upload_to=comprobante_abono_upload_path)
    hash_archivo = models.CharField(max_length=64, unique=True)
    valido = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # metadata OCR (mismo patrón que ComprobantePago)
    datos_extraidos = models.JSONField(blank=True, null=True)
    nro_operacion = models.CharField(max_length=100, blank=True, null=True)
    emisor_nombre = models.CharField(max_length=255, blank=True, null=True)
    emisor_cbu = models.CharField(max_length=22, blank=True, null=True)
    emisor_cuit = models.CharField(max_length=20, blank=True, null=True)
    fecha_detectada = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if not self.cliente:
            raise ValueError("ComprobanteAbono debe tener cliente asignado.")
        if not self.abono_mes:
            raise ValueError("ComprobanteAbono debe estar asociado a un AbonoMes.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"ComprobanteAbono #{self.pk} – AbonoMes {self.abono_mes_id}"

class PagoIntento(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="pagos", null=False)

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

    # --- Nuevos campos para trazabilidad ---
    hash_archivo = models.CharField(max_length=64, blank=True, null=True)
    ip_cliente = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-creado_en"]

    def save(self, *args, **kwargs):
        if not self.cliente:
            raise ValueError("PagoIntento debe tener cliente asignado.")
        if self.estado not in dict(self.ESTADOS):
            raise ValueError(f"Estado inválido: {self.estado}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.pk}] {self.usuario.email} - {self.estado}"

def comprobante_upload_path(instance, filename):
    return f"comprobantes/turno_{instance.turno.id}/{filename}"

class ComprobantePago(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="comprobantes",
        null=False,
        blank=False
    )
    turno = models.OneToOneField(
        "turnos_core.Turno",
        on_delete=models.CASCADE,
        related_name="comprobante",
        null=True,
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

    def save(self, *args, **kwargs):
        if not self.cliente:
            raise ValueError("ComprobantePago debe tener cliente asignado.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Comprobante de pago"
        verbose_name_plural = "Comprobantes de pago"
        ordering = ("-created_at",)

    def __str__(self):
        return f"Comprobante #{self.pk} – Turno {self.turno_id}"
