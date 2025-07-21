# apps/turnos_core/serializers.py
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.turnos_core.models import Lugar, BloqueoTurnos, Turno

class TurnoSerializer(serializers.ModelSerializer):
    servicio = serializers.CharField(source="servicio.nombre", read_only=True)
    recurso = serializers.SerializerMethodField()
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    lugar = serializers.CharField(source="lugar.nombre", read_only=True)

    class Meta:
        model = Turno
        fields = [
            "id", "fecha", "hora", "estado", "servicio", "recurso", "usuario", "lugar",
        ]

    def get_recurso(self, obj):
        if hasattr(obj, "recurso"):
            return str(obj.recurso)
        return None

class TurnoReservaSerializer(serializers.Serializer):
    turno_id = serializers.IntegerField()
    archivo = serializers.FileField()

    def validate(self, attrs):
        turno_id = attrs["turno_id"]
        user = self.context["request"].user

        try:
            turno = Turno.objects.get(pk=turno_id)
        except Turno.DoesNotExist:
            raise DRFValidationError({"turno_id": "El turno no existe."})

        if turno.usuario is not None:
            raise DRFValidationError({"turno_id": "Ese turno ya está reservado."})

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        turno_id = validated_data["turno_id"]
        archivo = validated_data["archivo"]

        try:
            comprobante = ComprobanteService.upload_comprobante(
                turno_id=turno_id,
                file_obj=archivo,
                usuario=user
            )
        except DjangoValidationError as e:
            # e.messages es una lista, devolvemos solo el primero para el usuario (UX clara)
            mensaje = e.messages[0] if hasattr(e, "messages") and e.messages else str(e)
            raise DRFValidationError({"error": f"Comprobante no válido: {mensaje}"})
        except DjangoPermissionDenied as e:
            raise DRFPermissionDenied({"error": str(e)})
        except Exception as e:
            # Cualquier otra excepción inesperada, controlada y sin traceback para el usuario
            raise DRFValidationError({"error": f"Error inesperado al validar comprobante: {str(e)}"})

        turno = comprobante.turno
        turno.usuario = user
        turno.estado = "reservado"
        # 2) Guardar ambos campos en la BD
        turno.save(update_fields=["usuario", "estado"])

        return turno

class TurnoDisponibleSerializer(serializers.ModelSerializer):
    hora = serializers.TimeField(format="%H:%M")
    class Meta:
        model = Turno
        fields = ["id", "fecha", "hora", "estado"]

class LugarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lugar
        fields = ["id", "nombre", "direccion"]

class BloqueoTurnosSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloqueoTurnos
        fields = "__all__"
