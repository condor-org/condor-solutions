# apps/auth_core/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True)
    tipo_usuario = models.CharField(max_length=30, blank=True)

    username = models.CharField(max_length=150, blank=True, null=True)  # Opcional, sin unicidad

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # Nada adicional obligatorio para superusuarios

    def __str__(self):
        return self.email
