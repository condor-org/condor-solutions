# apps/turnos_padel_core/models.py
from django.db import models
from apps.turnos_core.models import Lugar


class Profesor(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    especialidad = models.CharField(max_length=100, blank=True, null=True)
    activo = models.BooleanField(default=True)

    # Relación implícita a través de Disponibilidad
    sedes = models.ManyToManyField(
        Lugar,
        through="Disponibilidad",
        related_name="profesores"
    )

    def __str__(self):
        return self.nombre


class Disponibilidad(models.Model):
    profesor = models.ForeignKey("Profesor", on_delete=models.CASCADE, related_name="disponibilidades")
    lugar = models.ForeignKey(Lugar, on_delete=models.CASCADE)

    dia_semana = models.IntegerField(choices=[
        (0, "Lunes"), (1, "Martes"), (2, "Miércoles"),
        (3, "Jueves"), (4, "Viernes"), (5, "Sábado"), (6, "Domingo")
    ])
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)  # Permite pausar franjas sin borrar

    class Meta:
        unique_together = ("profesor", "lugar", "dia_semana", "hora_inicio", "hora_fin")

    def __str__(self):
        return f"{self.profesor} en {self.lugar} los {self.get_dia_semana_display()} de {self.hora_inicio} a {self.hora_fin}"
