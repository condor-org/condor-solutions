# apps/turnos_core/serializers.py

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.turnos_core.models import Lugar, BloqueoTurnos, Turno, Prestador, Disponibilidad

from django.contrib.auth import get_user_model
from apps.turnos_core.models import Prestador

Usuario = get_user_model()


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
            mensaje = e.messages[0] if hasattr(e, "messages") and e.messages else str(e)
            raise DRFValidationError({"error": f"Comprobante no válido: {mensaje}"})
        except DjangoPermissionDenied as e:
            raise DRFPermissionDenied({"error": str(e)})
        except Exception as e:
            raise DRFValidationError({"error": f"Error inesperado al validar comprobante: {str(e)}"})

        turno = comprobante.turno
        turno.usuario = user
        turno.estado = "reservado"
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


# ✅ NUEVOS SERIALIZERS

# apps/turnos_core/serializers.py

from rest_framework import serializers
from apps.turnos_core.models import Prestador

class PrestadorSerializer(serializers.ModelSerializer):
    nombre_publico = serializers.CharField()
    especialidad = serializers.CharField()
    foto = serializers.ImageField(required=False)
    activo = serializers.BooleanField()

    nombre = serializers.SerializerMethodField()
    apellido = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    tipo_usuario = serializers.SerializerMethodField()
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)

    class Meta:
        model = Prestador
        fields = [
            "id",
            "nombre_publico",
            "especialidad",
            "foto",
            "activo",
            "nombre",
            "apellido",
            "email",
            "telefono",
            "tipo_usuario",
            "cliente_nombre",
        ]

    def get_nombre(self, obj):
        user = self.context["request"].user
        if user.tipo_usuario == "admin_cliente" and obj.user:
            return obj.user.nombre
        return None

    def get_apellido(self, obj):
        user = self.context["request"].user
        if user.tipo_usuario == "admin_cliente" and obj.user:
            return obj.user.apellido
        return None

    def get_email(self, obj):
        user = self.context["request"].user
        if user.tipo_usuario == "admin_cliente" and obj.user:
            return obj.user.email
        return None

    def get_telefono(self, obj):
        user = self.context["request"].user
        if user.tipo_usuario == "admin_cliente" and obj.user:
            return obj.user.telefono
        return None

    def get_tipo_usuario(self, obj):
        user = self.context["request"].user
        if user.tipo_usuario == "admin_cliente" and obj.user:
            return obj.user.tipo_usuario
        return None



class DisponibilidadSerializer(serializers.ModelSerializer):
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




class PrestadorConUsuarioSerializer(serializers.ModelSerializer):
    # Campos del usuario embebidos
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)
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
        # Separar datos del usuario
        usuario_data = {
            "nombre": validated_data.pop("nombre", None),
            "apellido": validated_data.pop("apellido", None),
            "telefono": validated_data.pop("telefono", None),
        }

        usuario = instance.user
        for attr, value in usuario_data.items():
            if value is not None:
                setattr(usuario, attr, value)
        usuario.save()

        return super().update(instance, validated_data)


class PrestadorDisponibleSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    apellido = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Prestador
        fields = [
            "id", "nombre_publico", "especialidad", "foto", "disponibilidades",
            "nombre", "apellido", "email"
        ]

    def get_nombre(self, obj):
        return obj.user.first_name or ""

    def get_apellido(self, obj):
        return obj.user.last_name or ""

    def get_email(self, obj):
        return obj.user.email or ""
