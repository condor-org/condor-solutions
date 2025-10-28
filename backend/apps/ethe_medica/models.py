# apps/ethe_medica/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class Medico(models.Model):
    """
    Médico con categorías C1, C2, C3.
    Vinculado a Prestador (turnos_core) y Usuario (auth_core).
    """
    CATEGORIAS = [
        ("C1", "Médico C1"),
        ("C2", "Médico C2"),
        ("C3", "Médico C3"),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="medico_ethe"
    )
    
    prestador = models.OneToOneField(
        "turnos_core.Prestador",
        on_delete=models.CASCADE,
        related_name="medico_ethe",
        help_text="Vincula al sistema de turnos existente"
    )
    
    # Un médico puede ser C1, C2 y C3 a la vez
    categorias = models.JSONField(
        default=list,
        help_text="Lista de categorías: ['C1', 'C2', 'C3']"
    )
    
    matricula = models.CharField(max_length=50, unique=True)
    especialidad_medica = models.CharField(max_length=200, blank=True)
    
    # Centros donde puede trabajar (via Disponibilidad)
    # No hace falta campo extra, se usa Disponibilidad.lugar
    
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Médico ETHE"
        verbose_name_plural = "Médicos ETHE"
        indexes = [
            models.Index(fields=["activo"]),
            models.Index(fields=["matricula"]),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.matricula})"
    
    def tiene_categoria(self, categoria):
        """Verifica si el médico tiene una categoría específica (C1, C2, C3)"""
        return categoria in self.categorias
    
    def puede_atender_en_centro(self, centro):
        """Verifica si el médico tiene disponibilidad en un centro"""
        return self.prestador.disponibilidades.filter(
            lugar=centro, 
            activo=True
        ).exists()
    
    def clean(self):
        """Validar que el médico tenga al menos una categoría"""
        if not self.categorias or len(self.categorias) == 0:
            raise ValidationError("El médico debe tener al menos una categoría (C1, C2, C3)")
        
        # Validar que las categorías sean válidas
        categorias_validas = ["C1", "C2", "C3"]
        for categoria in self.categorias:
            if categoria not in categorias_validas:
                raise ValidationError(f"Categoría '{categoria}' no es válida. Debe ser: C1, C2, C3")


class Paciente(models.Model):
    """
    Paciente ingresado al sistema ETHE.
    Categoría dinámica según tests: C1, C2, C3.
    """
    CATEGORIAS = [
        ("C1", "Categoría 1"),
        ("C2", "Categoría 2"),
        ("C3", "Categoría 3"),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paciente_ethe"
    )
    
    # Categoría actual del paciente
    categoria_actual = models.CharField(
        max_length=2,
        choices=CATEGORIAS,
        help_text="Categoría según último test realizado"
    )
    
    # DNI/CUIL
    documento = models.CharField(max_length=20, unique=True)
    
    # Dónde fue ingresado
    centro_ingreso = models.ForeignKey(
        "turnos_core.Lugar",
        on_delete=models.SET_NULL,
        null=True,
        related_name="pacientes_ingresados"
    )
    
    medico_ingreso = models.ForeignKey(
        "Medico",
        on_delete=models.SET_NULL,
        null=True,
        related_name="pacientes_ingresados"
    )
    
    # Datos de contacto y residencia
    domicilio_calle = models.CharField(max_length=255)
    domicilio_ciudad = models.CharField(max_length=100)
    domicilio_provincia = models.CharField(max_length=100)
    domicilio_codigo_postal = models.CharField(max_length=10, blank=True)
    
    telefono_contacto = models.CharField(max_length=20)
    email_seguimiento = models.EmailField()
    
    # Datos adicionales
    fecha_nacimiento = models.DateField()
    obra_social = models.CharField(max_length=200, blank=True)
    
    # Estado
    activo = models.BooleanField(default=True)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    
    # Historial de categorías (auditoría)
    historial_categorias = models.JSONField(
        default=list,
        help_text="[{'categoria': 'C1', 'fecha': '...', 'motivo': '...'}, ...]"
    )
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paciente ETHE"
        verbose_name_plural = "Pacientes ETHE"
        indexes = [
            models.Index(fields=["categoria_actual"]),
            models.Index(fields=["documento"]),
            models.Index(fields=["activo"]),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.documento}) - {self.categoria_actual}"
    
    def cambiar_categoria(self, nueva_categoria, motivo=""):
        """Cambia la categoría del paciente y registra en historial"""
        self.historial_categorias.append({
            "categoria_anterior": self.categoria_actual,
            "categoria_nueva": nueva_categoria,
            "fecha": timezone.now().isoformat(),
            "motivo": motivo
        })
        self.categoria_actual = nueva_categoria
        self.save()


class ResultadoTest(models.Model):
    """
    Resultado de tests médicos realizados a pacientes.
    """
    TIPOS_TEST = [
        ("POCUS", "POCUS"),
        ("FIB4", "FIB4"),
        ("FIBROSCAN", "FIBROSCAN"),
    ]
    
    # POCUS
    POCUS_NORMAL = "NORMAL"
    POCUS_HG = "HG"  # Hígado Graso
    
    # FIB4
    FIB4_NR = "NR"  # No Riesgo
    FIB4_R = "R"    # Riesgo
    
    # FIBROSCAN
    FIBROSCAN_BAJO = "BAJO"
    FIBROSCAN_INTERMEDIO = "INTERMEDIO"
    FIBROSCAN_ALTO = "ALTO"
    
    RESULTADOS_POCUS = [
        (POCUS_NORMAL, "Normal"),
        (POCUS_HG, "Hígado Graso"),
    ]
    
    RESULTADOS_FIB4 = [
        (FIB4_NR, "No Riesgo"),
        (FIB4_R, "Riesgo"),
    ]
    
    RESULTADOS_FIBROSCAN = [
        (FIBROSCAN_BAJO, "Bajo"),
        (FIBROSCAN_INTERMEDIO, "Intermedio"),
        (FIBROSCAN_ALTO, "Alto"),
    ]
    
    paciente = models.ForeignKey(
        "Paciente",
        on_delete=models.CASCADE,
        related_name="resultados_tests"
    )
    
    tipo_test = models.CharField(max_length=20, choices=TIPOS_TEST)
    resultado = models.CharField(max_length=50)
    
    # Valores numéricos (opcional, para estadísticas)
    valor_numerico = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    fecha_realizacion = models.DateTimeField()
    
    centro = models.ForeignKey(
        "turnos_core.Lugar",
        on_delete=models.CASCADE,
        related_name="tests_realizados"
    )
    
    medico = models.ForeignKey(
        "Medico",
        on_delete=models.CASCADE,
        related_name="tests_realizados"
    )
    
    # Turno asociado (si corresponde)
    turno = models.ForeignKey(
        "turnos_core.Turno",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tests_realizados"
    )
    
    observaciones = models.TextField(blank=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Resultado de Test"
        verbose_name_plural = "Resultados de Tests"
        ordering = ["-fecha_realizacion"]
        indexes = [
            models.Index(fields=["paciente", "-fecha_realizacion"]),
            models.Index(fields=["tipo_test"]),
            models.Index(fields=["centro"]),
        ]
    
    def __str__(self):
        return f"{self.paciente} - {self.tipo_test}: {self.resultado}"
    
    def determinar_categoria_paciente(self):
        """
        Lógica de negocio: determina la categoría según el test.
        """
        if self.tipo_test == "POCUS":
            if self.resultado == self.POCUS_NORMAL:
                return None  # No ingresa al sistema
            elif self.resultado == self.POCUS_HG:
                # Esperar FIB4
                return None
        
        elif self.tipo_test == "FIB4":
            if self.resultado == self.FIB4_NR:
                return "C1"
            elif self.resultado == self.FIB4_R:
                return "C2"
        
        elif self.tipo_test == "FIBROSCAN":
            if self.resultado == self.FIBROSCAN_BAJO:
                return "C1"
            elif self.resultado == self.FIBROSCAN_INTERMEDIO:
                return "C2"
            elif self.resultado == self.FIBROSCAN_ALTO:
                return "C3"
        
        return None


class Establecimiento(models.Model):
    """
    Establecimiento físico que puede tener múltiples centros de atención.
    Ejemplo: Hospital Central puede tener C1, C2 y C3.
    """
    cliente = models.ForeignKey(
        "clientes_core.Cliente",
        on_delete=models.CASCADE,
        related_name="establecimientos_ethe"
    )
    
    nombre = models.CharField(max_length=200)
    direccion = models.TextField()
    telefono = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    
    # Datos administrativos
    admin_establecimiento = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="establecimientos_admin"
    )
    
    # Metadatos
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Establecimiento ETHE"
        verbose_name_plural = "Establecimientos ETHE"
        indexes = [
            models.Index(fields=["cliente", "activo"]),
        ]
    
    def __str__(self):
        return self.nombre
    
    def get_centros_por_categoria(self):
        """Obtiene centros agrupados por categoría"""
        centros = self.centros_ethe.all()
        return {
            "C1": [c for c in centros if "C1" in c.categorias],
            "C2": [c for c in centros if "C2" in c.categorias], 
            "C3": [c for c in centros if "C3" in c.categorias]
        }
    
    def tiene_categoria(self, categoria):
        """Verifica si el establecimiento tiene centros de una categoría"""
        return self.centros_ethe.filter(
            categorias__contains=[categoria]
        ).exists()


class CentroAtencion(models.Model):
    """
    Centro de atención específico dentro de un establecimiento.
    Un establecimiento puede tener múltiples centros (C1, C2, C3).
    """
    establecimiento = models.ForeignKey(
        "Establecimiento",
        on_delete=models.CASCADE,
        related_name="centros_ethe"
    )
    
    # Referencia al Lugar del sistema de turnos
    lugar = models.ForeignKey(
        "turnos_core.Lugar",
        on_delete=models.CASCADE,
        related_name="centros_atencion_ethe"
    )
    
    # Categorías que atiende este centro
    categorias = models.JSONField(
        default=list,
        help_text="Categorías que atiende: ['C1', 'C2', 'C3']"
    )
    
    # Configuración específica del centro
    nombre_centro = models.CharField(
        max_length=100,
        help_text="Nombre específico del centro (ej: 'Consultorios Hepatología')"
    )
    
    # Metadatos
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Centro de Atención ETHE"
        verbose_name_plural = "Centros de Atención ETHE"
        indexes = [
            models.Index(fields=["establecimiento", "activo"]),
        ]
    
    def __str__(self):
        return f"{self.establecimiento.nombre} - {self.nombre_centro}"
    
    def puede_atender_categoria(self, categoria):
        """Verifica si este centro puede atender una categoría"""
        return categoria in self.categorias


class JerarquiaCentro(models.Model):
    """
    Jerarquía entre centros de atención (puede ser dentro del mismo establecimiento).
    """
    centro_origen = models.ForeignKey(
        "CentroAtencion",
        on_delete=models.CASCADE,
        related_name="centros_siguientes"
    )
    
    centro_destino = models.ForeignKey(
        "CentroAtencion", 
        on_delete=models.CASCADE,
        related_name="centros_anteriores"
    )
    
    # Validar jerarquía: C1→C2, C2→C3
    categoria_origen = models.CharField(max_length=2)  # C1, C2
    categoria_destino = models.CharField(max_length=2)  # C2, C3
    
    # Configuración
    activo = models.BooleanField(default=True)
    prioridad = models.IntegerField(default=0)
    distancia_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Metadatos
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Jerarquía de Centro"
        verbose_name_plural = "Jerarquías de Centros"
        unique_together = ["centro_origen", "centro_destino"]
        ordering = ["-prioridad"]
        indexes = [
            models.Index(fields=["centro_origen", "activo"]),
        ]
    
    def __str__(self):
        return f"{self.centro_origen} → {self.centro_destino}"
    
    def clean(self):
        """Validar jerarquía correcta"""
        if self.categoria_origen == "C1" and self.categoria_destino != "C2":
            raise ValidationError("Centro C1 solo puede derivar a centros C2")
        if self.categoria_origen == "C2" and self.categoria_destino != "C3":
            raise ValidationError("Centro C2 solo puede derivar a centros C3")


class ProtocoloSeguimiento(models.Model):
    """
    Define protocolos de seguimiento por categoría de paciente.
    """
    categoria_paciente = models.CharField(
        max_length=2,
        choices=[("C1", "C1"), ("C2", "C2"), ("C3", "C3")],
        unique=True
    )
    
    nombre = models.CharField(max_length=100)  # PS1, PS2, PS3
    descripcion = models.TextField()
    
    # Frecuencia de seguimiento
    frecuencia_dias = models.IntegerField(
        help_text="Cada cuántos días debe tener seguimiento"
    )
    
    # Configuración adicional (JSON)
    configuracion = models.JSONField(
        default=dict,
        help_text="Configuración adicional del protocolo"
    )
    
    activo = models.BooleanField(default=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Protocolo de Seguimiento"
        verbose_name_plural = "Protocolos de Seguimiento"
    
    def __str__(self):
        return f"{self.nombre} - {self.categoria_paciente}"


class SeguimientoPaciente(models.Model):
    """
    Registro de seguimientos realizados a pacientes.
    """
    paciente = models.ForeignKey(
        "Paciente",
        on_delete=models.CASCADE,
        related_name="seguimientos"
    )
    
    protocolo = models.ForeignKey(
        "ProtocoloSeguimiento",
        on_delete=models.CASCADE
    )
    
    fecha_programada = models.DateField()
    fecha_realizada = models.DateTimeField(null=True, blank=True)
    
    estado = models.CharField(
        max_length=20,
        choices=[
            ("PENDIENTE", "Pendiente"),
            ("REALIZADO", "Realizado"),
            ("NO_ASISTIO", "No asistió"),
            ("CANCELADO", "Cancelado"),
        ],
        default="PENDIENTE"
    )
    
    observaciones = models.TextField(blank=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-fecha_programada"]
        indexes = [
            models.Index(fields=["paciente", "estado"]),
        ]
    
    def __str__(self):
        return f"{self.paciente} - {self.protocolo} ({self.estado})"


class HistorialCategoria(models.Model):
    """
    Historial de cambios de categoría de un paciente.
    Se crea automáticamente via signal al cambiar categoría.
    """
    paciente = models.ForeignKey(
        "Paciente",
        on_delete=models.CASCADE,
        related_name="historial_cambios_categoria"
    )
    
    categoria_anterior = models.CharField(
        max_length=2, 
        null=True, 
        blank=True,
        help_text="Categoría anterior del paciente"
    )
    categoria_nueva = models.CharField(
        max_length=2,
        help_text="Nueva categoría del paciente"
    )
    motivo = models.TextField(
        help_text="Motivo del cambio de categoría"
    )
    
    # Trazabilidad
    medico = models.ForeignKey(
        "Medico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Médico que realizó el cambio"
    )
    test_resultado = models.ForeignKey(
        "ResultadoTest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Test que causó el cambio"
    )
    
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-fecha_cambio"]
        verbose_name = "Historial de Categoría"
        verbose_name_plural = "Historiales de Categorías"
        indexes = [
            models.Index(fields=["paciente", "fecha_cambio"]),
        ]
    
    def __str__(self):
        return f"{self.paciente} - {self.categoria_anterior} → {self.categoria_nueva}"


# Signal para auto-crear HistorialCategoria
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Paciente)
def crear_historial_categoria(sender, instance, created, **kwargs):
    """
    Crea entrada en historial al cambiar categoría del paciente.
    """
    if not created:
        # Verificar si cambió la categoría
        try:
            old_instance = Paciente.objects.get(pk=instance.pk)
            if old_instance.categoria_actual != instance.categoria_actual:
                HistorialCategoria.objects.create(
                    paciente=instance,
                    categoria_anterior=old_instance.categoria_actual,
                    categoria_nueva=instance.categoria_actual,
                    motivo=f"Cambio de {old_instance.categoria_actual} a {instance.categoria_actual}"
                )
        except Paciente.DoesNotExist:
            # Si no existe la instancia anterior, no crear historial
            pass
