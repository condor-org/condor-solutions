# apps/turnos_core/serializers.py

from rest_framework import serializers
from apps.common.logging import LoggedModelSerializer
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.turnos_core.models import Lugar, Turno, Prestador, Disponibilidad, TurnoBonificado

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


# ------------------------------------------------------------------------------
# TurnoSerializer
# - Propósito: representar un Turno para lectura (list/retrieve).
# - Campos calculados:
#     * servicio: nombre del servicio (read-only).
#     * recurso: str() del GenericForeignKey (prestador u otro recurso).
#     * usuario: username del dueño (read-only).
#     * lugar: nombre de la sede (read-only).
#     * prestador_nombre: si el recurso es Prestador → nombre público (fallback email/str).
# ------------------------------------------------------------------------------
class TurnoSerializer(LoggedModelSerializer):
    servicio = serializers.CharField(source="servicio.nombre", read_only=True)
    recurso = serializers.SerializerMethodField()
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    lugar = serializers.CharField(source="lugar.nombre", read_only=True)
    prestador_nombre = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Turno
        fields = [
            "id", "fecha", "hora", "estado", "servicio", "recurso", "usuario", "lugar",
            "tipo_turno", "prestador_nombre", "reservado_para_abono",
        ]

    def get_recurso(self, obj):
        if hasattr(obj, "recurso"):
            return str(obj.recurso)
        return None

    def get_prestador_nombre(self, obj):
        """
        Si el recurso del turno es un Prestador, devolvemos su nombre público
        (o email del user, o str del recurso) sin modificar el modelo.
        """
        try:
            recurso = getattr(obj, "recurso", None)
            if recurso is None:
                return None
            from apps.turnos_core.models import Prestador  # evitar import circular
            if isinstance(recurso, Prestador):
                return (
                    getattr(recurso, "nombre_publico", None)
                    or getattr(getattr(recurso, "user", None), "email", None)
                    or str(recurso)
                )
            return None
        except Exception:
            return None


# ------------------------------------------------------------------------------
# TurnoReservaSerializer
# - Propósito: validar y ejecutar la reserva de un turno.
# - Input: turno_id, tipo_clase_id, usar_bonificado(bool), archivo(file si no usa bono).
# - Validaciones:
#     * turno existe y está libre.
#     * tipo de clase existe y corresponde a la sede del turno.
# - create():
#     * resuelve tipo_turno canónico (x1..x4) por code/codigo/alias.
#     * si usar_bonificado: busca bono vigente compatible y lo marca usado.
#     * si no: sube comprobante y crea PagoIntento(pre_aprobado).
#     * confirma reserva: setea usuario/estado/tipo_turno en Turno.
# - Side-effects: logs, PagoIntento; (las notifs se hacen en la view).
# ------------------------------------------------------------------------------
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

        # Sede consistente entre turno y tipo de clase
        sede_tipo = getattr(tipo_clase.configuracion_sede, "sede", None)
        if turno.lugar_id and sede_tipo and turno.lugar_id != sede_tipo.id:
            raise DRFValidationError({"tipo_clase_id": "El tipo de clase no corresponde a la sede del turno."})

        attrs["turno"] = turno
        attrs["tipo_clase"] = tipo_clase
        return attrs

    def create(self, validated_data):
        from django.db.models import Q  # import local para snippet autocontenible

        user = self.context["request"].user
        turno = validated_data["turno"]
        tipo_clase = validated_data["tipo_clase"]
        usar_bonificado = validated_data.get("usar_bonificado", False)
        archivo = validated_data.get("archivo")

        # --- Tipo de turno canónico (choices del modelo) ---
        tipo_turno = (getattr(tipo_clase, "codigo", "") or "").strip().lower()
        if tipo_turno not in {"x1", "x2", "x3", "x4"}:
            logger.warning(
                "[turno.reservar][tipo_invalido] user=%s turno=%s tipo_clase_id=%s codigo=%r",
                user.id, turno.id, getattr(tipo_clase, "id", None), getattr(tipo_clase, "codigo", None)
            )
            raise DRFValidationError({"tipo_clase_id": "Tipo de clase inválido para la reserva."})

        logger.debug(
            "[turno.reservar][tipo] user=%s turno=%s tipo=%s",
            user.id, turno.id, tipo_turno
        )

        if usar_bonificado:
            qs = (
                bonificaciones_vigentes(user)
                .filter(tipo_turno__iexact=tipo_turno)
                .order_by("fecha_creacion")
            )

            bono = qs.first()

            esc = ""
            try:
                desc = tipo_clase.get_codigo_display()
            except Exception:
                pass
            if not desc:
                desc = tipo_turno.upper()

            logger.info(
                "[turno.reservar][bono] user=%s turno=%s tipo=%s disponibles=%s elegido=%s",
                user.id, turno.id, tipo_turno, qs.count(), (getattr(bono, "id", None) if bono else None)
            )

            if not bono:
                raise DRFValidationError({
                    "usar_bonificado": f"No tenés bonificaciones disponibles para {desc}."
                })

            bono.marcar_usado(turno)

        else:
            # Requiere comprobante si no se usa bonificación
            if not archivo:
                raise DRFValidationError({
                    "archivo": "El comprobante es obligatorio si no usás turno bonificado."
                })

            try:
                comprobante = ComprobanteService.upload_comprobante(
                    turno_id=turno.id,
                    tipo_clase_id=tipo_clase.id,   # ← nuevo
                    file_obj=archivo,
                    usuario=user,
                    cliente=user.cliente,
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


        # Confirmar reserva en el Turno
        turno.usuario = user
        turno.estado = "reservado"
        turno.tipo_turno = tipo_turno
        turno.save(update_fields=["usuario", "estado", "tipo_turno"])

        logger.info(
            "[turno.reservar][ok] user=%s turno=%s estado=%s tipo_turno=%s",
            user.id, turno.id, turno.estado, turno.tipo_turno
        )
        return turno


# ------------------------------------------------------------------------------
# CancelarTurnoSerializer
# - Propósito: validar la cancelación de un turno por su dueño.
# - Input: turno_id.
# - Validaciones: existencia, pertenencia al usuario, estado=reservado y política de cancelación.
# - Output en validated_data: 'turno' listo para que la view ejecute la transacción y side-effects.
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# LugarSerializer
# - Propósito: exponer datos de sede (Lugar) con datos de pago leídos desde configuracion_padel.
# - Campos read-only: alias, cbu_cvu (nested source).
# ------------------------------------------------------------------------------
class LugarSerializer(LoggedModelSerializer):
    alias = serializers.CharField(source="configuracion_padel.alias", read_only=True)
    cbu_cvu = serializers.CharField(source="configuracion_padel.cbu_cvu", read_only=True)

    class Meta:
        model = Lugar
        fields = ["id", "nombre", "direccion", "alias", "cbu_cvu"]

# ------------------------------------------------------------------------------
# DisponibilidadSerializer
# - Propósito: CRUD de disponibilidades (prestador, sede, día/horario).
# - Validación: evita duplicados exactos (prestador/lugar/día/hora_inicio/hora_fin).
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# PrestadorDetailSerializer
# - Propósito: detalle de prestador con datos de usuario embebidos y disponibilidades.
# - Solo lectura en los campos del usuario.
# ------------------------------------------------------------------------------
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


# ------------------------------------------------------------------------------
# PrestadorConUsuarioSerializer
# - Propósito: alta/edición de prestadores con creación/actualización del Usuario embebido.
# - create():
#     * valida permisos (admin/super_admin), crea Usuario y luego Prestador.
#     * opcionalmente crea disponibilidades en bulk si vienen en el payload.
# - update():
#     * actualiza campos del Usuario (incluye set_password) y del Prestador.
#     * reemplaza disponibilidades si se envían (borra y bulk_create).
# ------------------------------------------------------------------------------
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

        # Crear disponibilidades iniciales si llegan en el payload
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

        # --- Reemplazar Disponibilidades (si llegan) ---
        disponibilidades_data = self.initial_data.get("disponibilidades", [])
        if disponibilidades_data:
            instance.disponibilidades.all().delete()
            from apps.turnos_core.models import Disponibilidad  # inline para evitar ciclos
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


# ------------------------------------------------------------------------------
# CrearTurnoBonificadoSerializer
# - Propósito: emisión manual de bonificaciones (vouchers) por admin.
# - Input: usuario_id, tipo_turno (x1..x4 o alias), motivo?, valido_hasta?.
# - Validaciones: usuario existe; mapeo de alias a code x1..x4.
# - create(): llama emitir_bonificacion_manual (service) con admin actual en context.
# ------------------------------------------------------------------------------
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

    # Campo explícito (duplicado a propósito para dejarlo visible arriba)
    tipo_turno = serializers.CharField()

    def create(self, validated_data):
        admin_user = self.context["request"].user
        User = get_user_model()
        usuario = User.objects.get(id=validated_data["usuario_id"])
        motivo = validated_data.get("motivo", "Bonificación manual")
        valido_hasta = validated_data.get("valido_hasta")
        tipo_turno = validated_data["tipo_turno"]  # obligatorio (ya normalizado)

        return emitir_bonificacion_manual(
            admin_user=admin_user,
            usuario=usuario,
            motivo=motivo,
            valido_hasta=valido_hasta,
            tipo_turno=tipo_turno,
        )


# ------------------------------------------------------------------------------
# Serializers de Cancelaciones Administrativas
# - Base: valida rango de fechas (y horas si ambas), motivo y dry_run por defecto.
# - Hijos: por sede (obligatorio sede_id, opcional prestador_ids) y por prestador (opcional sede_id).
# ------------------------------------------------------------------------------
class _CancelacionAdminBaseSerializer(serializers.Serializer):
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
    hora_inicio = serializers.TimeField(required=False, allow_null=True)
    hora_fin = serializers.TimeField(required=False, allow_null=True)
    motivo = serializers.CharField(required=False, allow_blank=True, default="Cancelación administrativa")
    dry_run = serializers.BooleanField(required=False, default=True)

    def validate(self, data):
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise serializers.ValidationError({"fecha_fin": "Debe ser >= fecha_inicio"})
        hi, hf = data.get("hora_inicio"), data.get("hora_fin")
        if hi and hf and hf <= hi:
            raise serializers.ValidationError({"hora_fin": "Debe ser > hora_inicio"})
        return data

    # (nota: hay un validate duplicado en el código original, lo dejamos tal cual para no modificar lógica)
    def validate(self, data):
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise serializers.ValidationError({"fecha_fin": "Debe ser >= fecha_inicio"})
        return data


class CancelacionPorSedeSerializer(_CancelacionAdminBaseSerializer):
    sede_id = serializers.IntegerField()
    # opcional: restringir a algunos profes de esa sede
    prestador_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )


class CancelacionPorPrestadorSerializer(_CancelacionAdminBaseSerializer):
    # opcional: acotar a una sede
    sede_id = serializers.IntegerField(required=False, allow_null=True)
