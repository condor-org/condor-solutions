from django.db import models

class Cliente(models.Model):
    TIPOS_CLIENTE = [
        ('padel', 'Club de Padel'),
        ('financiera', 'Financiera'),
        ('peluqueria', 'Peluquería'),
        # Agregá más verticales según necesidad.
    ]

    THEMES_VISUALES = [
        ('classic', 'Classic Theme'),
        ('alt', 'Alternative Theme'),
        # Agregá más si desarrollás otros themes.
    ]

    nombre = models.CharField(max_length=255)
    tipo_cliente = models.CharField(
        max_length=50,
        choices=TIPOS_CLIENTE,
        default='padel',
        help_text="Define el tipo de negocio del cliente."
    )

    theme = models.CharField(
        max_length=50,
        choices=THEMES_VISUALES,
        default='classic',
        help_text="Define el esquema visual general del cliente."
    )

    color_primario = models.CharField(max_length=20, blank=True, null=True)
    color_secundario = models.CharField(max_length=20, blank=True, null=True)

    logo = models.ImageField(upload_to='logos_clientes/', blank=True, null=True)
    configuraciones_extras = models.JSONField(blank=True, null=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_cliente_display()})"
