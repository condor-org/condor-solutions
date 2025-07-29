from django.db import models

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
        ConfiguracionSedePadel,
        on_delete=models.CASCADE,
        related_name="tipos_clase"
    )
    nombre = models.CharField(max_length=50)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nombre} ({self.configuracion_sede.sede.nombre}) - ${self.precio}"
