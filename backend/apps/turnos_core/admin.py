# condor/apps/turnos_core/admin.py

from django.contrib import admin
from apps.turnos_core.models import Turno, Servicio, Lugar


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "fecha", "servicio", "estado")
    list_filter  = ("usuario", "fecha", "estado", "servicio")
    search_fields = ("usuario__username", "servicio__nombre")
    ordering = ("-fecha",)


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "responsable", "lugar")
    search_fields = ("nombre", "responsable__username")

@admin.register(Lugar)
class LugarAdmin(admin.ModelAdmin):
    list_display = ("nombre", "direccion")  # Ajustá según tus campos
    search_fields = ("nombre",)

