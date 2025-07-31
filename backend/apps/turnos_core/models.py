# apps/turnos_core/models.py

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings  
from apps.clientes_core.models import Cliente 
from django.conf import settings
from django.utils import timezone

class Turno(models.Model):
    ESTADOS = [
        ("disponible", "Disponible"),
        ("reservado", "Reservado"),
        ("cancelado", "Cancelado"),
    ]

    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default="disponible")

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
        return f"{base} en {self.recurso}"


class Lugar(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="lugares", null=False)
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


class Prestador(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cliente = models.ForeignKey("clientes_core.Cliente", on_delete=models.CASCADE, related_name="prestadores")
    especialidad = models.CharField(max_length=100, blank=True, null=True)
    foto = models.ImageField(upload_to="prestadores/fotos/", blank=True, null=True)
    activo = models.BooleanField(default=True)
    nombre_publico = models.CharField(max_length=255) 
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.user)



class Disponibilidad(models.Model):
    prestador = models.ForeignKey("Prestador", on_delete=models.CASCADE, related_name="disponibilidades")
    lugar = models.ForeignKey("Lugar", on_delete=models.CASCADE, related_name="disponibilidades_core")
    dia_semana = models.IntegerField(choices=[
        (0, "Lunes"),
        (1, "Martes"),
        (2, "Miércoles"),
        (3, "Jueves"),
        (4, "Viernes"),
        (5, "Sábado"),
        (6, "Domingo")
    ])
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("prestador", "lugar", "dia_semana", "hora_inicio", "hora_fin")

    def __str__(self):
        return f"{self.prestador} en {self.lugar} los {self.get_dia_semana_display()} de {self.hora_inicio} a {self.hora_fin}"


class TurnoBonificado(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="turnos_bonificados")
    
    # Origen del vale (opcional)
    turno_original = models.ForeignKey(Turno, null=True, blank=True, on_delete=models.SET_NULL, related_name="bonificaciones_emitidas")
    
    # Turno al que se aplicó (si ya se usó)
    usado_en_turno = models.ForeignKey(Turno, null=True, blank=True, on_delete=models.SET_NULL, related_name="bonificacion_usada")
    
    # Audit info
    motivo = models.CharField(max_length=255, blank=True)
    generado_automaticamente = models.BooleanField(default=False)
    emitido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="bonificaciones_emitidas_manual")
    
    usado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    valido_hasta = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Turno bonificado"
        verbose_name_plural = "Turnos bonificados"

    def marcar_usado(self, turno):
        self.usado = True
        self.usado_en_turno = turno
        self.save()

    def esta_vigente(self):
        return not self.usado and (not self.valido_hasta or self.valido_hasta >= timezone.now().date())

    def __str__(self):
        return f"Bono para {self.usuario} ({'usado' if self.usado else 'activo'})"
