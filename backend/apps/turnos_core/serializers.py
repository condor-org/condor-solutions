# apps/turnos_core/serializers.py

from rest_framework import serializers
from apps.common.logging import LoggedModelSerializer
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.turnos_core.models import Lugar, BloqueoTurnos, Turno, Prestador, Disponibilidad, TurnoBonificado

from django.contrib.auth import get_user_model
from apps.pagos_core.models import PagoIntento
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.services.bonificaciones import (
    emitir_bonificacion_manual,
    bonificaciones_vigentes,
)

from apps.turnos_padel.models import TipoClasePadel

import logging
logger = logging.getLogger(__name__)



Usuario = get_user_model()


class TurnoSerializer(LoggedModelSerializer):
    servicio = serializers.CharField(source="servicio.nombre", read_only=True)
    recurso = serializers.SerializerMethodField()
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    lugar = serializers.CharField(source="lugar.nombre", read_only=True)

    class Meta:
        model = Turno
        fields = [
            "id", "fecha", "hora", "estado", "servicio", "recurso", "usuario", "lugar", "tipo_turno",
        ]

    def get_recurso(self, obj):
        if hasattr(obj, "recurso"):
            return str(obj.recurso)
        return None

class TurnoReservaSerializer(serializers.Serializer):
    turno_id = serializers.IntegerField()
    tipo_clase_id = serializers.IntegerField()
    archivo = serializers.FileField(required=False, allow_null=True)
    usar_bonificado = serializers.BooleanField(default=False)

    def validate(self, attrs):
        turno_id = attrs["turno_id"]
        tipo_clase_id = attrs["tipo_clase_id"]

        # Turno existente y libre
        try:
            turno = Turno.objects.get(pk=turno_id)
        except Turno.DoesNotExist:
            raise DRFValidationError({"turno_id": "El turno no existe."})
        if turno.usuario_id is not None:
            raise DRFValidationError({"turno_id": "Ese turno ya está reservado."})

        # Tipo de clase válido
        try:
            tipo_clase = TipoClasePadel.objects.select_related(
                "configuracion_sede", "configuracion_sede__sede"
            ).get(pk=tipo_clase_id)
        except TipoClasePadel.DoesNotExist:
            raise DRFValidationError({"tipo_clase_id": "El tipo de clase no existe."})

        # Sede consistente
        sede_tipo = getattr(tipo_clase.configuracion_sede, "sede", None)
        if turno.lugar_id and sede_tipo and turno.lugar_id != sede_tipo.id:
            raise DRFValidationError({"tipo_clase_id": "El tipo de clase no corresponde a la sede del turno."})

        attrs["turno"] = turno
        attrs["tipo_clase"] = tipo_clase
        return attrs

    def create(self, validated_data):
        from django.db.models import Q  # import local para mantener el snippet autocontenible

        user = self.context["request"].user
        turno = validated_data["turno"]
        tipo_clase = validated_data["tipo_clase"]
        usar_bonificado = validated_data.get("usar_bonificado", False)
        archivo = validated_data.get("archivo")

        # --- Resolver code canónico para tipo_turno (x1/x2/x3/x4) ---
        # 1) directo por atributos (code/codigo)
        tipo_turno = getattr(tipo_clase, "code", None) or getattr(tipo_clase, "codigo", None)

        # 2) si no, inferir desde display del choice o 'nombre' si existiera
        if not tipo_turno:
            try:
                display = tipo_clase.get_codigo_display() if hasattr(tipo_clase, "get_codigo_display") else ""
            except Exception:
                display = ""
            nombre_norm = (
                getattr(tipo_clase, "nombre", None)   # puede no existir en tu modelo actual
                or display
                or getattr(tipo_clase, "codigo", "")
            )
            nombre_norm = str(nombre_norm).strip().lower()

            mapping = {
                "individual": "x1", "x1": "x1",
                "2 personas": "x2", "x2": "x2",
                "3 personas": "x3", "x3": "x3",
                "4 personas": "x4", "x4": "x4",
            }
            tipo_turno = mapping.get(nombre_norm)

        logger.debug(
            "[TurnoReservaSerializer.create] user=%s turno=%s tipo_clase(id=%s) -> {code:%s,codigo:%s,display:%s} => tipo_turno=%s",
            user.id, turno.id, getattr(tipo_clase, "id", None),
            getattr(tipo_clase, "code", None),
            getattr(tipo_clase, "codigo", None),
            (tipo_clase.get_codigo_display() if hasattr(tipo_clase, "get_codigo_display") else None),
            tipo_turno,
        )

        if not tipo_turno:
            raise DRFValidationError({"tipo_clase_id": "Tipo de clase inválido para la reserva."})

        if usar_bonificado:
            # Aceptar alias históricos además del code (ej. "individual" para x1)
            alias_map = {
                "x1": {"x1", "individual"},
                "x2": {"x2", "2 personas"},
                "x3": {"x3", "3 personas"},
                "x4": {"x4", "4 personas"},
            }
            aliases = alias_map.get(tipo_turno, {tipo_turno})

            qs = bonificaciones_vigentes(user).filter(
                Q(tipo_turno__in=list(aliases))
            ).order_by("fecha_creacion")

            bono = qs.first()

            # Descripción amigable del tipo para el mensaje
            try:
                desc = tipo_clase.get_codigo_display() if hasattr(tipo_clase, "get_codigo_display") else ""
            except Exception:
                desc = ""
            if not desc:
                desc = getattr(tipo_clase, "codigo", "") or "esta clase"

            logger.info(
                "[turno.reservar][bono] user=%s turno=%s tipo=%s disponibles=%s elegido=%s",
                user.id, turno.id, tipo_turno, qs.count(), (getattr(bono, "id", None) if bono else None)
            )

            if not bono:
                raise DRFValidationError({
                    "usar_bonificado": f"No tenés bonificaciones disponibles para {desc}."
                })

            # Marcar bono usado en este turno
            bono.marcar_usado(turno)

        else:
            # Requiere comprobante si no usa bonificación
            if not archivo:
                raise DRFValidationError({
                    "archivo": "El comprobante es obligatorio si no usás turno bonificado."
                })

            try:
                comprobante = ComprobanteService.upload_comprobante(
                    turno_id=turno.id,
                    file_obj=archivo,
                    usuario=user,
                    cliente=user.cliente,
                    cbu_cvu=tipo_clase.configuracion_sede.cbu_cvu,
                    alias=tipo_clase.configuracion_sede.alias,
                    monto=tipo_clase.precio
                )
                logger.info(
                    "[turno.reservar][comprobante] user=%s turno=%s comp_id=%s monto=%s",
                    user.id, turno.id, getattr(comprobante, "id", None), tipo_clase.precio
                )
            except DjangoValidationError as e:
                mensaje = e.messages[0] if hasattr(e, "messages") else str(e)
                raise DRFValidationError({"error": f"Comprobante inválido: {mensaje}"})
            except DjangoPermissionDenied as e:
                raise DRFPermissionDenied({"error": str(e)})
            except Exception as e:
                logger.exception("[turno.reservar][comprobante][fail] user=%s turno=%s err=%s", user.id, turno.id, str(e))
                raise DRFValidationError({"error": f"Error inesperado: {str(e)}"})

            pi = PagoIntento.objects.create(
                cliente=user.cliente,
                usuario=user,
                estado="pre_aprobado",
                monto_esperado=tipo_clase.precio,
                moneda="ARS",
                alias_destino=tipo_clase.configuracion_sede.alias,
                cbu_destino=tipo_clase.configuracion_sede.cbu_cvu,
                content_type=ContentType.objects.get_for_model(comprobante),
                object_id=comprobante.id,
                tiempo_expiracion=timezone.now() + timezone.timedelta(minutes=60),
            )
            logger.info(
                "[turno.reservar][pago_intento] user=%s turno=%s intento_id=%s monto_esperado=%s",
                user.id, turno.id, getattr(pi, "id", None), tipo_clase.precio
            )

        # --- Confirmar reserva y setear tipo_turno en el turno ---
        turno.usuario = user
        turno.estado = "reservado"
        turno.tipo_turno = tipo_turno
        turno.save(update_fields=["usuario", "estado", "tipo_turno"])

        logger.info(
            "[turno.reservar][ok] user=%s turno=%s estado=%s tipo_turno=%s",
            user.id, turno.id, turno.estado, turno.tipo_turno
        )
        return turno

class CancelarTurnoSerializer(serializers.Serializer):
    turno_id = serializers.IntegerField()

    def validate(self, attrs):
        user = self.context["request"].user
        turno_id = attrs["turno_id"]

        try:
            turno = Turno.objects.get(id=turno_id)
        except Turno.DoesNotExist:
            raise DRFValidationError({"turno_id": "Turno no encontrado."})

        if turno.usuario != user:
            raise DRFPermissionDenied("No sos el dueño de este turno.")

        if turno.estado != "reservado":
            raise DRFValidationError({"turno_id": "El turno no está reservado o ya fue cancelado."})

        from apps.turnos_core.utils import cumple_politica_cancelacion
        if not cumple_politica_cancelacion(turno):
            raise DRFValidationError({"turno_id": "No se puede cancelar este turno según la política de cancelación."})

        attrs["turno"] = turno
        return attrs

class TurnoDisponibleSerializer(LoggedModelSerializer):
    hora = serializers.TimeField(format="%H:%M")
    class Meta:
        model = Turno
        fields = ["id", "fecha", "hora", "estado"]

class LugarSerializer(LoggedModelSerializer):
    alias = serializers.CharField(source="configuracion_padel.alias", read_only=True)
    cbu_cvu = serializers.CharField(source="configuracion_padel.cbu_cvu", read_only=True)

    class Meta:
        model = Lugar
        fields = ["id", "nombre", "direccion", "alias", "cbu_cvu"]

class BloqueoTurnosSerializer(LoggedModelSerializer):
    class Meta:
        model = BloqueoTurnos
        fields = "__all__"

class DisponibilidadSerializer(LoggedModelSerializer):
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

class PrestadorSerializer(LoggedModelSerializer):
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

class PrestadorDetailSerializer(LoggedModelSerializer):
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

class PrestadorConUsuarioSerializer(LoggedModelSerializer):
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
        disponibilidades_data = self.initial_data.get("disponibilidades", [])
        if disponibilidades_data:
            nuevas = []
            for d in disponibilidades_data:
                nuevas.append(Disponibilidad(
                    prestador=prestador,
                    lugar_id=d["lugar"],
                    dia_semana=d["dia_semana"],
                    hora_inicio=d["hora_inicio"],
                    hora_fin=d["hora_fin"],
                    activo=True
                ))
            Disponibilidad.objects.bulk_create(nuevas)

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

class CrearTurnoBonificadoSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField()
    motivo = serializers.CharField(required=False, allow_blank=True)
    valido_hasta = serializers.DateField(required=False)

    tipo_turno = serializers.CharField()

    def validate_tipo_turno(self, value):
        v = (value or "").strip().lower()
        mapping = {
            "individual": "x1", "x1": "x1",
            "2 personas": "x2", "x2": "x2",
            "3 personas": "x3", "x3": "x3",
            "4 personas": "x4", "x4": "x4",
        }
        code = mapping.get(v)
        if code not in {"x1", "x2", "x3", "x4"}:
            raise serializers.ValidationError("tipo_turno inválido (usar x1/x2/x3/x4 o nombres estándar).")
        return code

    def validate_usuario_id(self, value):
        User = get_user_model()
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Usuario no encontrado.")
        return value

    # ADD campo al serializer:
    tipo_turno = serializers.CharField()

    # REPLACE del método create():
    def create(self, validated_data):
        admin_user = self.context["request"].user
        User = get_user_model()
        usuario = User.objects.get(id=validated_data["usuario_id"])
        motivo = validated_data.get("motivo", "Bonificación manual")
        valido_hasta = validated_data.get("valido_hasta")
        tipo_turno = validated_data["tipo_turno"]  # obligatorio

        return emitir_bonificacion_manual(
            admin_user=admin_user,
            usuario=usuario,
            motivo=motivo,
            valido_hasta=valido_hasta,
            tipo_turno=tipo_turno,
        )

