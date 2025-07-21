# apps/turnos_padel_core/admin.py
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.timezone import now
from .models import Profesor, Disponibilidad
from apps.turnos_padel_core.services.generador import generar_turnos_del_mes


@admin.register(Profesor)
class ProfesorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "activo", "generar_turnos_link")
    list_filter = ("activo",)
    search_fields = ("nombre", "email")
    actions = ["generar_turnos_este_mes"]

    def generar_turnos_link(self, obj):
        return format_html("<em>Elegí arriba ⬆ y usá 'Acciones'</em>")

    generar_turnos_link.short_description = "Acción"

    def generar_turnos_este_mes(self, request, queryset):
        hoy = now()
        total = 0
        for profe in queryset:
            generar_turnos_del_mes(
                anio=hoy.year,
                mes=hoy.month,
                profesor_id=profe.id
            )
            total += 1
        self.message_user(request, f"✅ Se generaron turnos para {total} profesor(es).", messages.SUCCESS)

    generar_turnos_este_mes.short_description = "🗓️ Generar turnos del mes (por profe seleccionado)"


@admin.register(Disponibilidad)
class DisponibilidadAdmin(admin.ModelAdmin):
    list_display = ("profesor", "lugar", "dia_semana", "hora_inicio", "hora_fin", "activo")
    list_filter = ("dia_semana", "lugar", "activo")
    search_fields = ("profesor__nombre",)
