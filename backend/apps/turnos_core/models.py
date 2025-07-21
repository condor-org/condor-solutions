from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings  


class Servicio(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="servicios"
    )
    lugar = models.ForeignKey("Lugar", on_delete=models.SET_NULL, null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.lugar})" if self.lugar else self.nombre

class Turno(models.Model):
    ESTADOS = [
        ("disponible", "Disponible"),
        ("reservado", "Reservado"),
        ("cancelado", "Cancelado"),
    ]

    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")

    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True, related_name="turnos")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    recurso = GenericForeignKey("content_type", "object_id")

    lugar = models.ForeignKey("Lugar", on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("fecha", "hora", "content_type", "object_id")

    def __str__(self):
        base = f"{self.fecha} {self.hora} reservado por {self.usuario}"
        if self.servicio:
            return f"{base} - {self.servicio}"
        return f"{base} en {self.recurso}"

class Lugar(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.TextField(blank=True, null=True)
    referente = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.nombre

class BloqueoTurnos(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    recurso = GenericForeignKey("content_type", "object_id")

    lugar = models.ForeignKey(
        "Lugar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Si es nulo, bloqueo afecta a todas las sedes"
    )

    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    motivo = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        lugar_str = self.lugar.nombre if self.lugar else "Todas las sedes"
        return f"Bloqueo para {self.recurso} en {lugar_str} del {self.fecha_inicio} al {self.fecha_fin}"
