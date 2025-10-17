# apps/auth_core/models.py
"""
Modelos para el sistema multi-tenant con roles múltiples.
Permite que un usuario tenga diferentes roles en diferentes clientes.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario extendido para sistema multi-tenant.
    Soporta super admins globales y usuarios con roles específicos por cliente.
    """
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
    
    # Super admin es GLOBAL, no por cliente
    is_super_admin = models.BooleanField(
        default=False,
        help_text="Super admin tiene acceso total a todos los clientes"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # No obligamos nada adicional al email

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email

        # ✅ Validación de integridad: todos menos super_admin deben tener cliente
        if self.tipo_usuario != "super_admin" and not self.cliente:
            raise ValueError("Usuarios que no son super_admin deben tener un cliente asignado.")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.tipo_usuario})"

    def es_super_admin(self):
        """
        Verifica si el usuario es super admin global.
        """
        return self.is_super_admin


    def get_roles_en_cliente(self, cliente_id):
        """
        Obtiene TODOS los roles que tiene este usuario en un cliente específico.
        """
        if self.is_super_admin:
            return ["super_admin"]
        
        return list(self.clientes_roles.filter(
            cliente_id=cliente_id, 
            activo=True
        ).values_list('rol', flat=True))

    def tiene_acceso_a_cliente(self, cliente_id):
        """
        Verifica si el usuario tiene acceso a un cliente específico.
        Super admin tiene acceso a todos los clientes.
        """
        if self.is_super_admin:
            return True
        
        return self.clientes_roles.filter(cliente_id=cliente_id, activo=True).exists()

    def tiene_rol_en_cliente(self, cliente_id, rol):
        """
        Verifica si el usuario tiene un rol específico en un cliente.
        """
        if self.is_super_admin:
            return True
        
        return self.clientes_roles.filter(
            cliente_id=cliente_id,
            rol=rol,
            activo=True
        ).exists()

    def get_clientes_activos(self):
        """
        Obtiene todos los clientes a los que tiene acceso este usuario.
        """
        return self.clientes_roles.filter(activo=True).select_related('cliente')

    def agregar_rol_a_cliente(self, cliente, rol='usuario_final'):
        """
        Agrega un rol específico al usuario en un cliente.
        Super admin no necesita roles específicos.
        """
        if self.is_super_admin:
            return None
        
        user_client, created = UserClient.objects.get_or_create(
            usuario=self,
            cliente=cliente,
            rol=rol,
            defaults={'activo': True}
        )
        if not created and not user_client.activo:
            user_client.activo = True
            user_client.save()
        return user_client

    @property
    def cliente_actual(self):
        """
        Devuelve el UserClient activo para el cliente actual del usuario.
        Para super admins, devuelve None.
        Para usuarios con cliente asignado, devuelve el UserClient activo.
        """
        if self.is_super_admin:
            return None
        
        # Si el usuario tiene un cliente asignado directamente (sistema anterior)
        if self.cliente:
            user_client = self.clientes_roles.filter(
                cliente=self.cliente,
                activo=True
            ).first()
            if user_client:
                return user_client
        
        # Si no tiene cliente asignado directamente, buscar el primer UserClient activo
        return self.clientes_roles.filter(activo=True).first()


class UserClient(models.Model):
    """
    Relación muchos-a-muchos entre Usuario y Cliente con roles específicos.
    Permite que un usuario tenga diferentes roles en diferentes clientes.
    Ejemplo: Juan puede ser admin_cliente en ClienteA y usuario_final en ClienteB.
    """
    ROLES = [
        ("super_admin", "Super Admin"),
        ("admin_cliente", "Admin del Cliente"),
        ("empleado_cliente", "Empleado del Cliente"),
        ("usuario_final", "Usuario Final"),
        ("manager", "Manager"),
        ("coach", "Coach"),
        ("receptionist", "Recepcionista"),
        # Roles específicos por tipo de cliente
    ]

    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        related_name='clientes_roles',
        help_text="Usuario que tiene acceso al cliente"
    )
    cliente = models.ForeignKey(
        'clientes_core.Cliente', 
        on_delete=models.CASCADE, 
        related_name='usuarios_roles',
        help_text="Cliente al que tiene acceso el usuario"
    )
    rol = models.CharField(
        max_length=30, 
        choices=ROLES,
        help_text="Rol que tiene el usuario en este cliente específico"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si el acceso está activo"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['usuario', 'cliente', 'rol']
        indexes = [
            models.Index(fields=['usuario', 'cliente']),
            models.Index(fields=['cliente', 'activo']),
        ]

    def __str__(self):
        return f"{self.usuario.email} -> {self.cliente.nombre} ({self.rol})"
