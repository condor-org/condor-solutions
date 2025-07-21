# apps/turnos_padel_core/serializers.py
from rest_framework import serializers
from apps.turnos_padel.models import Disponibilidad, Lugar, Profesor
from apps.turnos_core.models import Turno


class ProfesorDisponibleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profesor
        fields = ("id", "nombre", "email", "telefono", "especialidad")



class TurnoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Turno
        fields = [
            "id", "fecha", "hora",
            "estado", "lugar", "usuario",
            # agrega campos extra que necesites
        ]


class DisponibilidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disponibilidad
        fields = (
            "id",
            "dia_semana",
            "hora_inicio",
            "hora_fin",
            "lugar",
            "activo",
        )

class ProfesorSerializer(serializers.ModelSerializer):
    disponibilidades = DisponibilidadSerializer(many=True)

    class Meta:
        model = Profesor
        fields = (
            "id",
            "nombre",
            "email",
            "telefono",
            "especialidad",
            "activo",
            "disponibilidades",
        )

    def create(self, validated_data):
        disponibilidades_data = validated_data.pop("disponibilidades", [])
        profesor = Profesor.objects.create(**validated_data)
        for disp_data in disponibilidades_data:
            Disponibilidad.objects.create(profesor=profesor, **disp_data)
        return profesor

    def update(self, instance, validated_data):
        disponibilidades_data = validated_data.pop("disponibilidades", [])
        
        # Actualizar campos del profesor
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualizar disponibilidades
        # Opción simple: borrar todas y recrear (más segura)
        instance.disponibilidades.all().delete()
        for disp_data in disponibilidades_data:
            Disponibilidad.objects.create(profesor=instance, **disp_data)

        return instance
