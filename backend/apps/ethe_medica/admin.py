# apps/ethe_medica/admin.py

from django.contrib import admin
from .models import (
    Medico, Paciente, ResultadoTest, Establecimiento, CentroAtencion, JerarquiaCentro,
    ProtocoloSeguimiento, SeguimientoPaciente
)


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ['user', 'matricula', 'categorias', 'especialidad_medica', 'activo']
    list_filter = ['categorias', 'activo', 'creado_en']
    search_fields = ['user__nombre', 'user__apellido', 'matricula']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    def save_model(self, request, obj, form, change):
        """Validar que el médico tenga al menos una categoría antes de guardar"""
        obj.clean()  # Ejecutar validaciones del modelo
        super().save_model(request, obj, form, change)
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('user', 'matricula', 'especialidad_medica')
        }),
        ('Categorías Médicas', {
            'fields': ('categorias',)
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ['user', 'documento', 'categoria_actual', 'centro_ingreso', 'activo']
    list_filter = ['categoria_actual', 'activo', 'fecha_ingreso']
    search_fields = ['user__nombre', 'user__apellido', 'documento']
    readonly_fields = ['fecha_ingreso', 'creado_en', 'actualizado_en']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('user', 'documento', 'fecha_nacimiento', 'obra_social')
        }),
        ('Categorización', {
            'fields': ('categoria_actual', 'centro_ingreso', 'medico_ingreso')
        }),
        ('Contacto', {
            'fields': ('telefono_contacto', 'email_seguimiento')
        }),
        ('Domicilio', {
            'fields': ('domicilio_calle', 'domicilio_ciudad', 'domicilio_provincia', 'domicilio_codigo_postal')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Historial', {
            'fields': ('historial_categorias',),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('fecha_ingreso', 'creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ResultadoTest)
class ResultadoTestAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'tipo_test', 'resultado', 'fecha_realizacion', 'centro', 'medico']
    list_filter = ['tipo_test', 'resultado', 'fecha_realizacion', 'centro']
    search_fields = ['paciente__user__nombre', 'paciente__user__apellido', 'medico__user__nombre']
    readonly_fields = ['creado_en']
    date_hierarchy = 'fecha_realizacion'
    
    fieldsets = (
        ('Información del Test', {
            'fields': ('paciente', 'tipo_test', 'resultado', 'valor_numerico')
        }),
        ('Contexto', {
            'fields': ('fecha_realizacion', 'centro', 'medico', 'turno')
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
        ('Fechas', {
            'fields': ('creado_en',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Establecimiento)
class EstablecimientoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'direccion', 'admin_establecimiento', 'activo']
    list_filter = ['activo', 'creado_en']
    search_fields = ['nombre', 'direccion', 'admin_establecimiento__nombre']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    fieldsets = (
        ('Información del Establecimiento', {
            'fields': ('nombre', 'direccion', 'telefono', 'email')
        }),
        ('Administración', {
            'fields': ('cliente', 'admin_establecimiento')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CentroAtencion)
class CentroAtencionAdmin(admin.ModelAdmin):
    list_display = ['nombre_centro', 'establecimiento', 'categorias', 'activo']
    list_filter = ['categorias', 'activo', 'establecimiento']
    search_fields = ['nombre_centro', 'establecimiento__nombre']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    fieldsets = (
        ('Información del Centro', {
            'fields': ('establecimiento', 'lugar', 'nombre_centro', 'categorias')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(JerarquiaCentro)
class JerarquiaCentroAdmin(admin.ModelAdmin):
    list_display = ['centro_origen', 'centro_destino', 'categoria_origen', 'categoria_destino', 'prioridad', 'activo']
    list_filter = ['categoria_origen', 'categoria_destino', 'activo']
    search_fields = ['centro_origen__nombre_centro', 'centro_destino__nombre_centro']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    fieldsets = (
        ('Jerarquía', {
            'fields': ('centro_origen', 'centro_destino', 'categoria_origen', 'categoria_destino')
        }),
        ('Configuración', {
            'fields': ('prioridad', 'distancia_km')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProtocoloSeguimiento)
class ProtocoloSeguimientoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria_paciente', 'frecuencia_dias', 'activo']
    list_filter = ['categoria_paciente', 'activo']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    fieldsets = (
        ('Información del Protocolo', {
            'fields': ('categoria_paciente', 'nombre', 'descripcion', 'frecuencia_dias')
        }),
        ('Configuración', {
            'fields': ('configuracion',)
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SeguimientoPaciente)
class SeguimientoPacienteAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'protocolo', 'fecha_programada', 'estado', 'fecha_realizada']
    list_filter = ['estado', 'fecha_programada', 'protocolo']
    search_fields = ['paciente__user__nombre', 'paciente__user__apellido']
    readonly_fields = ['creado_en', 'actualizado_en']
    date_hierarchy = 'fecha_programada'
    
    fieldsets = (
        ('Seguimiento', {
            'fields': ('paciente', 'protocolo', 'fecha_programada')
        }),
        ('Realización', {
            'fields': ('estado', 'fecha_realizada', 'observaciones')
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )
