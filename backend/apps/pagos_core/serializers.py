# apps/pagos_core/serializers.py

from rest_framework import serializers
from apps.common.logging import LoggedModelSerializer
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
            turno = Turno.objects.select_related("usuario").get(pk=turno_id)
        except Turno.DoesNotExist:
            raise serializers.ValidationError({"turno_id": "Turno no encontrado"})

        # 2. Validar propiedad o control del cliente
        if (
            user.tipo_usuario == "usuario_final" and turno.usuario_id != user.id
        ) or (
            user.tipo_usuario == "admin_cliente" and turno.usuario.cliente_id != user.cliente_id
        ):
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
            validated_data["cliente"] = self.context["request"].user.cliente
            comprobante = ComprobanteService.upload_comprobante(
                turno_id=turno_id,
                file_obj=archivo,
                usuario=usuario
            )
            return comprobante

        except DjangoValidationError as e:
            raise serializers.ValidationError({"error": e.messages})


class ComprobantePagoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    usuario_email = serializers.SerializerMethodField()
    turno_hora = serializers.SerializerMethodField()
    profesor_nombre = serializers.SerializerMethodField()
    sede_nombre = serializers.SerializerMethodField()
    especialidad_nombre = serializers.SerializerMethodField()
    cliente_nombre = serializers.SerializerMethodField()

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
            "profesor_nombre",
            "sede_nombre",
            "especialidad_nombre",
            "cliente_nombre",
        ]

    def get_usuario_nombre(self, obj):
        try:
            return (
                obj.turno.usuario.get_full_name()
                or obj.turno.usuario.username
                or obj.turno.usuario.email
            )
        except Exception as e:
            print(f"[DEBUG] usuario_nombre ERROR comprobante {obj.id}: {e}")
            return ""

    def get_usuario_email(self, obj):
        try:
            return obj.turno.usuario.email
        except Exception as e:
            print(f"[DEBUG] usuario_email ERROR comprobante {obj.id}: {e}")
            return ""

    def get_turno_hora(self, obj):
        try:
            return obj.turno.hora.strftime("%H:%M")
        except Exception as e:
            print(f"[DEBUG] turno_hora ERROR comprobante {obj.id}: {e}")
            return None

    def get_profesor_nombre(self, obj):
        try:
            recurso = obj.turno.recurso
            if hasattr(recurso, "nombre_publico"):
                return recurso.nombre_publico
            return str(recurso)
        except Exception as e:
            print(f"[DEBUG] profesor_nombre ERROR comprobante {obj.id}: {e}")
            return ""

    def get_sede_nombre(self, obj):
        try:
            return obj.turno.lugar.nombre
        except Exception as e:
            print(f"[DEBUG] sede_nombre ERROR comprobante {obj.id}: {e}")
            return ""

    def get_cliente_nombre(self, obj):
        try:
            return obj.turno.lugar.cliente.nombre
        except Exception as e:
            print(f"[DEBUG] cliente_nombre ERROR comprobante {obj.id}: {e}")
            return ""

    def get_especialidad_nombre(self, obj):
        try:
            recurso = obj.turno.recurso
            if hasattr(recurso, "especialidad"):
                return recurso.especialidad
            return ""
        except Exception as e:
            print(f"[DEBUG] especialidad_nombre ERROR comprobante {obj.id}: {e}")
            return ""


class TurnoReservaSerializer(serializers.Serializer):
    turno_id = serializers.IntegerField()
    archivo = serializers.FileField(required=False)

    def validate(self, attrs):
        turno_id = attrs["turno_id"]
        archivo = attrs.get("archivo")
        user = self.context["request"].user

        try:
            turno = Turno.objects.select_related("usuario", "prestador__cliente").get(pk=turno_id)
        except Turno.DoesNotExist:
            raise serializers.ValidationError({"turno_id": "El turno no existe."})

        if turno.usuario is not None:
            raise serializers.ValidationError({"turno_id": "Ese turno ya está reservado."})

        # --- Validación por tipo de usuario ---
        if user.tipo_usuario == "usuario_final":
            # 🔒 usuario_final DEBE subir archivo
            if not archivo:
                raise serializers.ValidationError({"archivo": "Debés subir un comprobante."})

            if turno.prestador.cliente_id != user.cliente_id:
                raise serializers.ValidationError({"turno_id": "No tenés acceso a este turno."})

            # Validación de archivo
            max_size = 3 * 1024 * 1024
            if archivo.size > max_size:
                raise serializers.ValidationError({"archivo": "El archivo no puede superar 3 MB"})

            ext = archivo.name.rsplit(".", 1)[-1].lower()
            allowed_ext = {"pdf", "png", "jpg", "jpeg", "webp", "bmp"}
            if ext not in allowed_ext:
                raise serializers.ValidationError({"archivo": f"Extensión no permitida: {ext}"})

        elif user.tipo_usuario == "admin_cliente":
            # ✅ puede reservar sin archivo
            if turno.prestador.cliente_id != user.cliente_id:
                raise serializers.ValidationError({"turno_id": "No tenés acceso a este turno."})

        else:
            raise serializers.ValidationError("No tenés permiso para reservar turnos.")

        return attrs

    def create(self, validated_data):
        from apps.pagos_core.services.comprobantes import ComprobanteService

        user = self.context["request"].user
        turno_id = validated_data["turno_id"]
        archivo = validated_data.get("archivo")

        turno = Turno.objects.get(pk=turno_id)

        # ✅ Caso admin_cliente: sin comprobante
        if user.tipo_usuario == "admin_cliente":
            turno.usuario = user
            turno.estado = "reservado"
            turno.save(update_fields=["usuario", "estado"])
            return turno

        # 🧾 Caso usuario_final: procesar comprobante
        comprobante = ComprobanteService.upload_comprobante(
            turno_id=turno_id,
            file_obj=archivo,
            usuario=user
        )

        turno = comprobante.turno
        turno.usuario = user
        turno.estado = "reservado"
        turno.save(update_fields=["usuario", "estado"])

        return turno



class ConfiguracionPagoSerializer(LoggedModelSerializer):
    class Meta:
        model = ConfiguracionPago
        fields = "__all__"
