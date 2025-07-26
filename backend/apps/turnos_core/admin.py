# condor/apps/turnos_core/admin.py

from django.contrib import admin
from apps.turnos_core.models import Turno, Lugar


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "fecha", "estado")
    list_filter  = ("usuario", "fecha", "estado")
    search_fields = ("usuario__username",)
    ordering = ("-fecha",)


@admin.register(Lugar)
class LugarAdmin(admin.ModelAdmin):
    list_display = ("nombre", "direccion")  # Ajustá según tus campos
    search_fields = ("nombre",)

