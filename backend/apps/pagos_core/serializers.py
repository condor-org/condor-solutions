# apps/pagos_core/serializers.py

from rest_framework import serializers
from apps.common.logging import LoggedModelSerializer
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.turnos_core.models import Turno
from apps.pagos_core.models import ComprobantePago
from apps.turnos_padel.models import AbonoMes  # 🧩 requerido por ComprobanteAbonoUploadSerializer


class ComprobanteUploadSerializer(serializers.Serializer):
    """
    Subida de comprobante para un turno individual.
    - Valida existencia y pertenencia del turno (multi-tenant).
    - Aplica validaciones básicas de archivo (extensión/peso).
    """
    turno_id = serializers.IntegerField()
    archivo = serializers.FileField()

    def validate(self, attrs):
        turno_id = attrs["turno_id"]
        archivo = attrs["archivo"]
        user = self.context["request"].user

        # 1) Turno existente
        try:
            turno = Turno.objects.select_related("usuario").get(pk=turno_id)
        except Turno.DoesNotExist:
            raise serializers.ValidationError({"turno_id": "Turno no encontrado"})

        # 2) Scope por rol/cliente
        if (
            user.tipo_usuario == "usuario_final" and turno.usuario_id != user.id
        ) or (
            user.tipo_usuario == "admin_cliente" and turno.usuario.cliente_id != user.cliente_id
        ):
            raise serializers.ValidationError({"turno_id": "No tenés permiso sobre este turno"})

        # 3) Archivo: tamaño/extensión (hard limit 3MB; extensiones controladas)
        max_size = 3 * 1024 * 1024  # 3MB
        if archivo.size > max_size:
            raise serializers.ValidationError({"archivo": "El archivo no puede superar 3 MB"})

        ext = archivo.name.rsplit(".", 1)[-1].lower()
        allowed_ext = {"pdf", "png", "jpg", "jpeg", "webp", "bmp"}
        if ext not in allowed_ext:
            raise serializers.ValidationError({"archivo": f"Extensión no permitida: {ext}"})

        return attrs

    def create(self, validated_data):
        """
        Delegamos el procesamiento a ComprobanteService (OCR + reglas).
        """
        from apps.pagos_core.services.comprobantes import ComprobanteService

        turno_id = validated_data["turno_id"]
        archivo = validated_data["archivo"]
        usuario = self.context["request"].user

        try:
            # Hints de contexto para el service (cliente)
            validated_data["cliente"] = usuario.cliente
            comprobante = ComprobanteService.upload_comprobante(
                turno_id=turno_id,
                file_obj=archivo,
                usuario=usuario
            )
            return comprobante
        except DjangoValidationError as e:
            # Normalizamos a DRF ValidationError
            raise serializers.ValidationError({"error": e.messages})


class ComprobantePagoSerializer(LoggedModelSerializer):
    """
    Serializer de lectura para listados de comprobantes.
    - Enriquece con datos denormalizados del turno (usuario, profesor, sede, cliente).
    - Usa LoggedModelSerializer para trazabilidad de serialización.
    """
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

    # ⚠️ En estos getters se usa print() para logs de error.
    #    Recomendación: migrar a logging.getLogger(__name__).exception(...) para consistencia.

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
    """
    Reserva de un turno (con/sin comprobante según rol).
    - usuario_final: requiere archivo (comprobante).
    - admin_cliente: puede reservar sin archivo.
    - Valida existencia del turno, que no esté reservado, y pertenencia al cliente.
    """
    turno_id = serializers.IntegerField()
    archivo = serializers.FileField(required=False)

    def validate(self, attrs):
        turno_id = attrs["turno_id"]
        archivo = attrs.get("archivo")
        user = self.context["request"].user

        # Turno existente y libre
        try:
            turno = Turno.objects.select_related("usuario", "prestador__cliente").get(pk=turno_id)
        except Turno.DoesNotExist:
            raise serializers.ValidationError({"turno_id": "El turno no existe."})
        if turno.usuario is not None:
            raise serializers.ValidationError({"turno_id": "Ese turno ya está reservado."})

        # Reglas por rol
        if user.tipo_usuario == "usuario_final":
            # Debe subir comprobante y el turno debe pertenecer a su cliente
            if not archivo:
                raise serializers.ValidationError({"archivo": "Debés subir un comprobante."})
            if turno.prestador.cliente_id != user.cliente_id:
                raise serializers.ValidationError({"turno_id": "No tenés acceso a este turno."})

            # Validación básica del archivo (mismo criterio que ComprobanteUploadSerializer)
            max_size = 3 * 1024 * 1024
            if archivo.size > max_size:
                raise serializers.ValidationError({"archivo": "El archivo no puede superar 3 MB"})
            ext = archivo.name.rsplit(".", 1)[-1].lower()
            allowed_ext = {"pdf", "png", "jpg", "jpeg", "webp", "bmp"}
            if ext not in allowed_ext:
                raise serializers.ValidationError({"archivo": f"Extensión no permitida: {ext}"})

        elif user.tipo_usuario == "admin_cliente":
            # Puede reservar sin archivo pero debe pertenecer a su cliente
            if turno.prestador.cliente_id != user.cliente_id:
                raise serializers.ValidationError({"turno_id": "No tenés acceso a este turno."})
        else:
            # Otros roles no participan de este flujo
            raise serializers.ValidationError("No tenés permiso para reservar turnos.")

        return attrs

    def create(self, validated_data):
        """
        Persiste la reserva:
        - admin_cliente: sin comprobante.
        - usuario_final: sube comprobante y luego reserva.
        """
        from apps.pagos_core.services.comprobantes import ComprobanteService

        user = self.context["request"].user
        turno_id = validated_data["turno_id"]
        archivo = validated_data.get("archivo")

        turno = Turno.objects.get(pk=turno_id)

        # admin_cliente → reserva directa
        if user.tipo_usuario == "admin_cliente":
            turno.usuario = user
            turno.estado = "reservado"
            turno.save(update_fields=["usuario", "estado"])
            return turno

        # usuario_final → procesa comprobante antes de reservar
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


class ComprobanteAbonoUploadSerializer(serializers.Serializer):
    """
    Subida de comprobante para un AbonoMes (y aplicación opcional de bonificaciones).
    - `archivo` es requerido solo si el neto a pagar > 0 (lo decide el view/service).
    - `bonificaciones_ids` puede venir vacío (lista opcional).
    """
    abono_mes_id = serializers.IntegerField()
    archivo = serializers.FileField(required=False)  # sólo si monto > 0
    bonificaciones_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    def validate(self, attrs):
        user = self.context["request"].user
        # Abono existente y del mismo cliente
        try:
            abono = AbonoMes.objects.select_related("sede__cliente").get(pk=attrs["abono_mes_id"])
        except AbonoMes.DoesNotExist:
            raise serializers.ValidationError({"abono_mes_id": "Abono no encontrado"})
        if abono.sede.cliente_id != getattr(user, "cliente_id", None):
            raise serializers.ValidationError({"abono_mes_id": "No tenés permiso sobre este abono"})
        return attrs

    def create(self, validated_data):
        """
        Delegamos el procesamiento al service de comprobantes de abono.
        """
        from apps.pagos_core.services.comprobantes import ComprobanteService
        usuario = self.context["request"].user
        return ComprobanteService.upload_comprobante_abono(
            abono_mes_id=validated_data["abono_mes_id"],
            file_obj=validated_data.get("archivo"),
            usuario=usuario,
            cliente=getattr(usuario, "cliente", None),
            bonificaciones_ids=validated_data.get("bonificaciones_ids") or [],
        )
