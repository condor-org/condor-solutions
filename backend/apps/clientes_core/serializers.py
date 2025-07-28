from rest_framework import serializers
from apps.clientes_core.models import Cliente

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            'id',
            'nombre',
            'tipo_cliente',
            'theme',                # Agregado
            'logo',
            'color_primario',
            'color_secundario',
            'configuraciones_extras',
        ]
