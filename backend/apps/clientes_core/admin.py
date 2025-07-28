from django.contrib import admin
from apps.clientes_core.models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        'nombre',
        'tipo_cliente',
        'theme',               # Agregado para ver el theme desde el listado
        'color_primario',
        'color_secundario',
        'actualizado_en',
    )
    list_filter = ('tipo_cliente', 'theme')  # Filtro por tipo_cliente y theme
    search_fields = ('nombre',)
