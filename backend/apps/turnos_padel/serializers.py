# apps/turnos_padel/serializers.py
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from apps.turnos_padel.models import ConfiguracionSedePadel, TipoClasePadel
from apps.turnos_core.models import Lugar

class TipoClasePadelSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)  # Permite crear sin ID
    class Meta:
        model = TipoClasePadel
        fields = ["id", "nombre", "precio"]

class ConfiguracionSedePadelSerializer(serializers.ModelSerializer):
    tipos_clase = TipoClasePadelSerializer(many=True)

    class Meta:
        model = ConfiguracionSedePadel
        fields = ["id", "alias", "cbu_cvu", "tipos_clase"]

    def update(self, instance, validated_data):
        tipos_data = validated_data.pop("tipos_clase", [])

        # Actualizar alias y CBU
        instance.alias = validated_data.get("alias", instance.alias)
        instance.cbu_cvu = validated_data.get("cbu_cvu", instance.cbu_cvu)
        instance.save()

        # IDs enviados desde frontend
        enviados_ids = [td.get("id") for td in tipos_data if td.get("id")]

        # Eliminar tipos que no están
        instance.tipos_clase.exclude(id__in=enviados_ids).delete()

        # Crear o actualizar tipos
        for tipo_data in tipos_data:
            tipo_id = tipo_data.get("id")
            if tipo_id:
                tipo = instance.tipos_clase.get(id=tipo_id)
                tipo.nombre = tipo_data.get("nombre", tipo.nombre)
                tipo.precio = tipo_data.get("precio", tipo.precio)
                tipo.save()
            else:
                TipoClasePadel.objects.create(configuracion_sede=instance, **tipo_data)

        return instance

class SedePadelSerializer(serializers.ModelSerializer):
    configuracion_padel = ConfiguracionSedePadelSerializer()

    class Meta:
        model = Lugar
        fields = [
            "id", "nombre", "direccion", "referente", "telefono", "configuracion_padel"
        ]

    def create(self, validated_data):
        config_data = validated_data.pop("configuracion_padel", {})
        tipos_data = config_data.pop("tipos_clase", [])

        user = self.context["request"].user
        cliente = user.cliente if user.tipo_usuario != "super_admin" else validated_data.get("cliente")

        # Crear sede
        sede = Lugar.objects.create(cliente=cliente, **validated_data)

        # Crear configuración
        config = ConfiguracionSedePadel.objects.create(
            sede=sede,
            alias=config_data.get("alias", ""),
            cbu_cvu=config_data.get("cbu_cvu", "")
        )

        # Crear tipos
        if tipos_data:
            for tipo in tipos_data:
                TipoClasePadel.objects.create(configuracion_sede=config, **tipo)
        else:
            for nombre in ["Individual", "2 Personas", "3 Personas", "4 Personas"]:
                TipoClasePadel.objects.create(configuracion_sede=config, nombre=nombre, precio=0)

        return sede

    def update(self, instance, validated_data):
        config_data = validated_data.pop("configuracion_padel", {})
        tipos_data = config_data.pop("tipos_clase", [])

        # Actualizar datos sede
        for field in ["nombre", "direccion", "referente", "telefono"]:
            setattr(instance, field, validated_data.get(field, getattr(instance, field)))
        instance.save()

        # Crear configuración si no existe
        config = getattr(instance, "configuracion_padel", None)
        if not config:
            config = ConfiguracionSedePadel.objects.create(sede=instance)

        # Actualizar configuración
        config.alias = config_data.get("alias", config.alias)
        config.cbu_cvu = config_data.get("cbu_cvu", config.cbu_cvu)
        config.save()

        # Sincronizar tipos
        enviados_ids = [t.get("id") for t in tipos_data if t.get("id")]
        config.tipos_clase.exclude(id__in=enviados_ids).delete()
        for tipo in tipos_data:
            if "id" in tipo:
                obj = config.tipos_clase.get(id=tipo["id"])
                obj.nombre = tipo.get("nombre", obj.nombre)
                obj.precio = tipo.get("precio", obj.precio)
                obj.save()
            else:
                TipoClasePadel.objects.create(configuracion_sede=config, **tipo)

        return instance
