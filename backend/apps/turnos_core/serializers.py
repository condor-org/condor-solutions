# apps/turnos_core/serializers.py

from rest_framework import serializers
from apps.common.serializers import DebugSerializerMixin
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.turnos_core.models import Lugar, BloqueoTurnos, Turno, Prestador, Disponibilidad

from django.contrib.auth import get_user_model
from apps.turnos_core.models import Prestador
from apps.pagos_core.models import PagoIntento
from django.utils import timezone

Usuario = get_user_model()


class TurnoSerializer(DebugSerializerMixin, serializers.ModelSerializer):
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


class TurnoReservaSerializer(DebugSerializerMixin, serializers.Serializer):
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
            mensaje = e.messages[0] if hasattr(e, "messages") and e.messages else str(e)
            raise DRFValidationError({"error": f"Comprobante no válido: {mensaje}"})
        except DjangoPermissionDenied as e:
            raise DRFPermissionDenied({"error": str(e)})
        except Exception as e:
            raise DRFValidationError({"error": f"Error inesperado al validar comprobante: {str(e)}"})

        # Creamos el intento de pago asociado al comprobante y turno
        turno = comprobante.turno
        pago_intento = PagoIntento.objects.create(
            cliente=user.cliente,
            usuario=user,
            estado="pre_aprobado",
            monto_esperado=comprobante.datos_extraidos.get("monto", 0),
            moneda="ARS",
            alias_destino=comprobante.datos_extraidos.get("alias", ""),
            cbu_destino=comprobante.datos_extraidos.get("cbu_destino", ""),
            content_type=ContentType.objects.get_for_model(comprobante),
            object_id=comprobante.id,
            tiempo_expiracion=timezone.now() + timezone.timedelta(minutes=60),
        )

        turno.usuario = user
        turno.estado = "reservado"
        turno.save(update_fields=["usuario", "estado"])
        return turno


class TurnoDisponibleSerializer(DebugSerializerMixin, serializers.ModelSerializer):
    hora = serializers.TimeField(format="%H:%M")
    class Meta:
        model = Turno
        fields = ["id", "fecha", "hora", "estado"]

class LugarSerializer(DebugSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Lugar
        fields = ["id", "nombre", "direccion"]

class BloqueoTurnosSerializer(DebugSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = BloqueoTurnos
        fields = "__all__"

class DisponibilidadSerializer(DebugSerializerMixin, serializers.ModelSerializer):
    lugar_nombre = serializers.CharField(source="lugar.nombre", read_only=True)

    class Meta:
        model = Disponibilidad
        fields = [
            "id", "prestador", "lugar", "lugar_nombre", "dia_semana",
            "hora_inicio", "hora_fin", "activo"
        ]
        read_only_fields = ["id", "lugar_nombre"]

    def validate(self, attrs):
        qs = Disponibilidad.objects.filter(
            prestador=attrs["prestador"],
            lugar=attrs["lugar"],
            dia_semana=attrs["dia_semana"],
            hora_inicio=attrs["hora_inicio"],
            hora_fin=attrs["hora_fin"],
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise DRFValidationError("Ya existe una disponibilidad con los mismos datos.")
        return attrs

class PrestadorSerializer(DebugSerializerMixin, serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)

    class Meta:
        model = Prestador
        fields = [
            "id",
            "nombre_publico",
            "especialidad",
            "foto",
            "activo",
            "cliente_nombre",
        ]

class PrestadorDetailSerializer(DebugSerializerMixin, serializers.ModelSerializer):
    # Datos del usuario embebidos solo lectura
    nombre = serializers.CharField(source="user.nombre", read_only=True)
    apellido = serializers.CharField(source="user.apellido", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    telefono = serializers.CharField(source="user.telefono", read_only=True)
    tipo_usuario = serializers.CharField(source="user.tipo_usuario", read_only=True)

    disponibilidades = DisponibilidadSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)

    class Meta:
        model = Prestador
        fields = [
            "id",
            "nombre_publico",
            "especialidad",
            "foto",
            "activo",
            "cliente_nombre",
            "nombre", "apellido", "email", "telefono", "tipo_usuario",
            "disponibilidades"
        ]

class PrestadorConUsuarioSerializer(DebugSerializerMixin, serializers.ModelSerializer):
    # Campos del usuario embebidos
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    nombre = serializers.CharField(write_only=True)
    apellido = serializers.CharField(write_only=True, required=False, allow_blank=True)
    telefono = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # Campos del prestador
    especialidad = serializers.CharField(required=False, allow_blank=True)
    nombre_publico = serializers.CharField(required=False, allow_blank=True)
    activo = serializers.BooleanField(default=True)

    class Meta:
        model = Prestador
        fields = [
            "id",
            "email", "password", "nombre", "apellido", "telefono",  # user
            "especialidad", "foto", "activo", "nombre_publico"       # prestador
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        request = self.context["request"]
        admin_user = request.user

        if admin_user.tipo_usuario not in ("super_admin", "admin_cliente"):
            raise DRFPermissionDenied("No tenés permisos para crear prestadores.")

        # Extraer datos del usuario
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        nombre = validated_data.pop("nombre")
        apellido = validated_data.pop("apellido", "")
        telefono = validated_data.pop("telefono", "")

        # Crear usuario
        nuevo_usuario = Usuario.objects.create_user(
            username=email,
            email=email,
            password=password,
            nombre=nombre,
            apellido=apellido,
            telefono=telefono,
            tipo_usuario="empleado_cliente",
            cliente=admin_user.cliente,
        )

        # Armar nombre_publico si no vino
        nombre_publico = validated_data.pop("nombre_publico", f"{nombre} {apellido}".strip())

        # Crear prestador
        prestador = Prestador.objects.create(
            user=nuevo_usuario,
            cliente=admin_user.cliente,
            nombre_publico=nombre_publico,
            **validated_data
        )

        return prestador


    def update(self, instance, validated_data):
        request = self.context["request"]
        usuario = instance.user

        # --- Actualizar campos del Usuario ---
        usuario_data = {
            "nombre": validated_data.pop("nombre", None),
            "apellido": validated_data.pop("apellido", None),
            "telefono": validated_data.pop("telefono", None),
            "password": validated_data.pop("password", None),
        }

        for attr, value in usuario_data.items():
            if value:
                if attr == "password":
                    usuario.set_password(value)
                else:
                    setattr(usuario, attr, value)
        usuario.save()


        # --- Actualizar Prestador ---
        instance.especialidad = validated_data.get("especialidad", instance.especialidad)
        instance.nombre_publico = validated_data.get("nombre_publico", instance.nombre_publico)
        instance.activo = validated_data.get("activo", instance.activo)
        if "foto" in validated_data:
            instance.foto = validated_data["foto"]
        instance.save()

        # --- Actualizar Disponibilidades ---
        disponibilidades_data = self.initial_data.get("disponibilidades", [])

        if disponibilidades_data:
            # Limpiar anteriores (puede cambiarse por lógica más compleja si querés mergear)
            instance.disponibilidades.all().delete()

            from apps.turnos_core.models import Disponibilidad  # importar inline si es necesario

            nuevas = []
            for d in disponibilidades_data:
                nuevas.append(Disponibilidad(
                    prestador=instance,
                    lugar_id=d["lugar"],
                    dia_semana=d["dia_semana"],
                    hora_inicio=d["hora_inicio"],
                    hora_fin=d["hora_fin"],
                    activo=True
                ))
            Disponibilidad.objects.bulk_create(nuevas)

        return instance
