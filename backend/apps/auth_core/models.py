# apps/auth_core/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ROLES = [
        ("super_admin", "Super Admin"),
        ("admin_cliente", "Admin del Cliente"),
        ("empleado_cliente", "Empleado del Cliente"),
        ("usuario_final", "Usuario Final"),
    ]

    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True)
    tipo_usuario = models.CharField(max_length=30, choices=ROLES, default="usuario_final")
    cliente = models.ForeignKey(
        'clientes_core.Cliente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Nulo solo para superadmins."
    )
    username = models.CharField(max_length=150, blank=True, null=True, unique=False)

    oauth_provider = models.CharField(max_length=50, blank=True, null=True)
    oauth_uid = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # No obligamos nada adicional al email

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.tipo_usuario})"
