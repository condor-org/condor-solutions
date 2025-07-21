# apps/pagos_core/serializers.py

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.turnos_core.models import Turno
from apps.pagos_core.models import ComprobantePago
from .models import ConfiguracionPago


class ComprobanteUploadSerializer(serializers.Serializer):
    turno_id = serializers.IntegerField()
    archivo = serializers.FileField()

    def validate(self, attrs):
        turno_id = attrs["turno_id"]
        archivo = attrs["archivo"]
        user = self.context["request"].user

        # 1. Validar que el turno exista
        try:
            turno = Turno.objects.get(pk=turno_id)
        except Turno.DoesNotExist:
            raise serializers.ValidationError({"turno_id": "Turno no encontrado"})

        # 2. Validar propiedad del turno
        if turno.usuario_id != user.id and not user.is_staff:
            raise serializers.ValidationError({"turno_id": "No tenés permiso sobre este turno"})

        # 3. Validaciones básicas de archivo
        max_size = 3 * 1024 * 1024  # 3MB
        if archivo.size > max_size:
            raise serializers.ValidationError({"archivo": "El archivo no puede superar 3 MB"})

        ext = archivo.name.rsplit(".", 1)[-1].lower()
        allowed_ext = {"pdf", "png", "jpg", "jpeg", "webp", "bmp"}
        if ext not in allowed_ext:
            raise serializers.ValidationError({"archivo": f"Extensión no permitida: {ext}"})

        return attrs

    def create(self, validated_data):
        from apps.pagos_core.services.comprobantes import ComprobanteService

        turno_id = validated_data["turno_id"]
        archivo = validated_data["archivo"]
        usuario = self.context["request"].user

        try:
            comprobante = ComprobanteService.upload_comprobante(
                turno_id=turno_id,
                file_obj=archivo,
                usuario=usuario
            )
            return comprobante

        except DjangoValidationError as e:
            # ✔️ Convierte a DRF
            raise serializers.ValidationError({"error": e.messages})


class ComprobantePagoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    usuario_email = serializers.SerializerMethodField()
    turno_hora = serializers.SerializerMethodField()

    class Meta:
        model = ComprobantePago
        fields = [
            "id",
            "created_at",
            "turno_id",
            "valido",
            "datos_extraidos",
            "usuario_nombre",
            "usuario_email",
             "turno_hora", 
        ]

    def get_usuario_nombre(self, obj):
        try:
            return obj.turno.usuario.get_full_name() or obj.turno.usuario.username or obj.turno.usuario.email
        except AttributeError:
            return ""
    
    def get_usuario_email(self, obj):
        try:
            return obj.turno.usuario.email
        except AttributeError:
            return ""

    
    def get_turno_hora(self, obj):
        try:
            return obj.turno.hora.strftime("%H:%M")
        except AttributeError:
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
            raise serializers.ValidationError({"turno_id": "El turno no existe."})

        if turno.usuario is not None:
            raise serializers.ValidationError({"turno_id": "Ese turno ya está reservado."})

        return attrs

    def create(self, validated_data):
        from apps.pagos_core.services.comprobantes import ComprobanteService

        user = self.context["request"].user
        turno_id = validated_data["turno_id"]
        archivo = validated_data["archivo"]

        comprobante = ComprobanteService.upload_comprobante(
            turno_id=turno_id,
            file_obj=archivo,
            usuario=user
        )

        turno = comprobante.turno
        turno.usuario = user
        turno.save(update_fields=["usuario"])

        return turno


class ConfiguracionPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionPago
        fields = "__all__"
