from django.contrib import admin
from .models import AbonoMes, ConfiguracionSedePadel, TipoClasePadel, TipoAbonoPadel


@admin.register(AbonoMes)
class AbonoMesAdmin(admin.ModelAdmin):
    list_display = [
        "id", "usuario", "sede", "prestador", "anio", "mes", 
        "dia_semana", "hora", "tipo_clase", "configuracion_personalizada_display", 
        "monto", "estado", "creado_en"
    ]
    list_filter = [
        "estado", "sede", "prestador", "anio", "mes", "dia_semana",
        "tipo_clase__isnull",  # Para distinguir normales vs personalizados
        "creado_en"
    ]
    search_fields = [
        "usuario__email", "usuario__nombre", "sede__nombre", 
        "prestador__nombre", "configuracion_personalizada"
    ]
    readonly_fields = ["creado_en", "actualizado_en"]
    list_per_page = 25
    
    def configuracion_personalizada_display(self, obj):
        """Muestra la configuración personalizada de forma legible"""
        if obj.configuracion_personalizada:
            configs = []
            for config in obj.configuracion_personalizada:
                tipo_nombre = config.get('codigo', 'N/A')
                cantidad = config.get('cantidad', 0)
                configs.append(f"{tipo_nombre} x{cantidad}")
            return " | ".join(configs)
        return "—"
    configuracion_personalizada_display.short_description = "Configuración Personalizada"


@admin.register(ConfiguracionSedePadel)
class ConfiguracionSedePadelAdmin(admin.ModelAdmin):
    list_display = ["sede", "alias", "cbu_cvu"]
    search_fields = ["sede__nombre", "alias", "cbu_cvu"]


@admin.register(TipoClasePadel)
class TipoClasePadelAdmin(admin.ModelAdmin):
    list_display = ["configuracion_sede", "codigo", "precio", "activo"]
    list_filter = ["activo", "configuracion_sede__sede"]
    search_fields = ["codigo", "configuracion_sede__sede__nombre"]


@admin.register(TipoAbonoPadel)
class TipoAbonoPadelAdmin(admin.ModelAdmin):
    list_display = ["configuracion_sede", "codigo", "precio", "activo"]
    list_filter = ["activo", "configuracion_sede__sede"]
    search_fields = ["codigo", "configuracion_sede__sede__nombre"]
