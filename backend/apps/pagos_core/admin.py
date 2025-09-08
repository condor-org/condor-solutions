# condor/apps/pagos_core/admin.py

from django.contrib import admin
from apps.pagos_core.models import PagoIntento, ComprobantePago


@admin.register(PagoIntento)
class PagoIntentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "estado",
        "monto_esperado",
        "moneda",
        "alias_destino",
        "cbu_destino",
        "tiempo_expiracion",
        "creado_en",
    )
    list_filter = (
        "estado",
        "moneda",
        "creado_en",
        "tiempo_expiracion",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
        "external_reference",
        "id_transaccion_banco",
        "alias_destino",
    )
    ordering = ("-creado_en",)
    autocomplete_fields = ("usuario",)
    date_hierarchy = "creado_en"


@admin.register(ComprobantePago)
class ComprobantePagoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "turno",
        "nro_operacion",
        "fecha_detectada",
        "emisor_nombre",
        "emisor_cbu",
        "valido",
        "created_at",
    )
    list_filter = (
        "valido",
        "created_at",
    )
    search_fields = (
        "turno__usuario__username",
        "nro_operacion",
        "emisor_nombre",
        "emisor_cbu",
        "hash_archivo",
    )
    readonly_fields = (
        "hash_archivo",
        "datos_extraidos",
        "archivo",
        "fecha_detectada",
        "emisor_nombre",
        "emisor_cbu",
        "emisor_cuit",
    )
    ordering = ("-created_at",)

