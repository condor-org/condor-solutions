# apps/turnos_core/serializers.py

from rest_framework import serializers
from apps.common.logging import LoggedModelSerializer
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.turnos_core.models import Lugar, Turno, Prestador, Disponibilidad, TurnoBonificado
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from apps.pagos_core.models import PagoIntento
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.services.bonificaciones import (
    emitir_bonificacion_manual,
    bonificaciones_vigentes,
)
from django.db import models,transaction

from apps.turnos_padel.models import TipoClasePadel

import logging
from datetime import time

logger = logging.getLogger(__name__)

Usuario = get_user_model()

# ------------------------------------------------------------------------------
# Helpers para validación de solapamiento de horarios
# ------------------------------------------------------------------------------

def _to_time(v):
    """Acepta time, 'HH:MM' o 'HH:MM:SS' y devuelve datetime.time."""
    if isinstance(v, time):
        return v
    if not v:
        raise DRFValidationError("Hora inválida")
    s = str(v)
    if len(s) == 5:  # HH:MM
        s = s + ":00"
    try:
        hh, mm, ss = map(int, s.split(":"))
        return time(hh, mm, ss)
    except Exception:
        raise DRFValidationError(f"Hora inválida: {v!r}")

def _rango_solapa(inicio1, fin1, inicio2, fin2):
    """Verifica si dos rangos [ini, fin) se solapan. Usa datetime.time."""
    i1, f1 = _to_time(inicio1), _to_time(fin1)
    i2, f2 = _to_time(inicio2), _to_time(fin2)
    return i1 < f2 and i2 < f1


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
# TurnoReservaSerializer (actualizado)
# - Agrega: bonificacion_id (opcional)
# - Lógica:
#      precio_turno = TipoClasePadel.precio
#      valor_bono = TurnoBonificado.valor (si se envía/elige uno válido)
#      restante = max(precio_turno - valor_bono, 0)
#      Si restante > 0 → exigir comprobante; si restante == 0 → sin comprobante.
#      Marca la bonificación como usada (aunque cubra parcial o totalmente).
# ------------------------------------------------------------------------------

class TurnoReservaSerializer(serializers.Serializer):
    turno_id = serializers.IntegerField()
    tipo_clase_id = serializers.IntegerField()
    archivo = serializers.FileField(required=False, allow_null=True)
    bonificacion_id = serializers.IntegerField(required=False, allow_null=True)

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
        user = self.context["request"].user
        turno_in = validated_data["turno"]
        tipo_clase = validated_data["tipo_clase"]
        bonificacion_id = validated_data.get("bonificacion_id")
        archivo = validated_data.get("archivo")

        # --- Tipo de turno canónico ---
        tipo_turno = (getattr(tipo_clase, "codigo", "") or "").strip().lower()
        if tipo_turno not in {"x1", "x2", "x3", "x4"}:
            logger.warning(
                "[turno.reservar][tipo_invalido] user=%s turno=%s tipo_clase_id=%s codigo=%r",
                getattr(user, "id", None),
                getattr(turno_in, "id", None),
                getattr(tipo_clase, "id", None),
                getattr(tipo_clase, "codigo", None),
            )
            raise DRFValidationError({"tipo_clase_id": "Tipo de clase inválido para la reserva."})

        precio_turno = float(getattr(tipo_clase, "precio", 0) or 0)
        code_alias = {
            "x1": "individual", "x2": "2 personas", "x3": "3 personas", "x4": "4 personas"
        }.get(tipo_turno, "")

        with transaction.atomic():
            # Lock del turno
            turno = Turno.objects.select_for_update().get(pk=turno_in.id)

            if turno.usuario_id is not None or turno.estado != "disponible":
                raise DRFValidationError({"turno_id": "Ese turno ya fue tomado."})

            # === Bonificación: SOLO la enviada por FE ===
            bono = None
            if bonificacion_id is not None:
                try:
                    bonificacion_id = int(bonificacion_id)
                except (TypeError, ValueError):
                    raise DRFValidationError({"bonificacion_id": "Debés seleccionar una bonificación válida."})

                bono = (
                    TurnoBonificado.objects
                    .select_for_update()
                    .only("id", "valor", "tipo_turno", "valido_hasta", "usado", "usuario_id")
                    .filter(
                        id=bonificacion_id,
                        usuario=user,
                        usado=False,
                    )
                    .filter(models.Q(valido_hasta__isnull=True) | models.Q(valido_hasta__gte=timezone.localdate()))
                    .filter(models.Q(tipo_turno__iexact=tipo_turno) | models.Q(tipo_turno__iexact=code_alias))
                    .first()
                )
                if not bono:
                    raise DRFValidationError({
                        "bonificacion_id": "La bonificación indicada no está disponible o no aplica a este turno."
                    })

            # Valor del bono (si corresponde)
            valor_bono = float(getattr(bono, "valor", 0) or 0)
            if valor_bono < 0:
                raise DRFValidationError({"bonificacion_id": "La bonificación seleccionada tiene un valor inválido."})

            # Restante = precio_turno - valor_bono (no menor a 0)
            restante = max(precio_turno - valor_bono, 0.0)

            # Comprobante solo si queda restante
            comprobante = None
            if restante > 0:
                if not archivo:
                    raise DRFValidationError({"archivo": "Falta comprobante para cubrir el monto restante."})
                try:
                    comprobante = ComprobanteService.upload_comprobante(
                        turno_id=turno.id,
                        tipo_clase_id=tipo_clase.id,
                        file_obj=archivo,
                        usuario=user,
                        cliente=user.cliente,
                    )
                    logger.info(
                        "[turno.reservar][comprobante] user=%s turno=%s comp_id=%s restante=%.2f precio=%.2f bono=%.2f",
                        user.id, turno.id, getattr(comprobante, "id", None),
                        restante, precio_turno, valor_bono
                    )
                except DjangoValidationError as e:
                    mensaje = e.messages[0] if hasattr(e, "messages") else str(e)
                    raise DRFValidationError({"error": f"Comprobante inválido: {mensaje}"})
                except DjangoPermissionDenied as e:
                    raise DRFPermissionDenied({"error": str(e)})
                except Exception as e:
                    logger.exception("[turno.reservar][comprobante][fail] user=%s turno=%s err=%s", user.id, turno.id, str(e))
                    raise DRFValidationError({"error": f"Error inesperado: {str(e)}"})

            # Consumir bonificación (si hay)
            if bono:
                logger.info(
                    "[turno.reservar][bono] user=%s turno=%s bono=%s valor=%.2f precio=%.2f restante=%.2f",
                    user.id, turno.id, bono.id, valor_bono, precio_turno, restante
                )
                bono.marcar_usado(turno)

            # Confirmar reserva
            turno.usuario = user
            turno.estado = "reservado"
            turno.tipo_turno = tipo_turno
            turno.save(update_fields=["usuario", "estado", "tipo_turno"])

            logger.info(
                "[turno.reservar][ok] user=%s turno=%s estado=%s tipo_turno=%s restante=%.2f",
                user.id, turno.id, turno.estado, turno.tipo_turno, restante
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
        # Validar duplicados exactos
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
        
        # Validar overlap de horarios
        self._validar_overlap(attrs)
        return attrs
    
    def _validar_overlap(self, attrs):
        """Valida que no haya solapamiento de horarios para el mismo prestador, lugar y día."""
        prestador = attrs["prestador"]
        lugar = attrs["lugar"]
        dia_semana = attrs["dia_semana"]
        hora_inicio = attrs["hora_inicio"]
        hora_fin = attrs["hora_fin"]
        
        # Buscar disponibilidades existentes que puedan solaparse
        disponibilidades_existentes = Disponibilidad.objects.filter(
            prestador=prestador,
            lugar=lugar,
            dia_semana=dia_semana,
            activo=True
        )
        
        if self.instance:
            disponibilidades_existentes = disponibilidades_existentes.exclude(pk=self.instance.pk)
        
        for disp in disponibilidades_existentes:
            if self._hay_solapamiento(hora_inicio, hora_fin, disp.hora_inicio, disp.hora_fin):
                raise DRFValidationError(
                    f"Ya existe una disponibilidad para {prestador.nombre_publico} en {lugar.nombre} "
                    f"los {disp.get_dia_semana_display()} que se solapa con el horario "
                    f"{disp.hora_inicio} - {disp.hora_fin}. "
                    f"El prestador no puede tener turnos solapados."
                )
    
    def _hay_solapamiento(self, inicio1, fin1, inicio2, fin2):
        """Verifica si dos rangos de tiempo se solapan."""
        return _rango_solapa(inicio1, fin1, inicio2, fin2)

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

        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(self.context['request'])
        
        if not admin_user.is_super_admin and rol_actual != "admin_cliente":
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
            # Validar overlap solo entre las nuevas disponibilidades
            self._validar_overlap_nuevas_disponibilidades(disponibilidades_data)
            
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
            # Validar overlap solo entre las nuevas disponibilidades
            self._validar_overlap_nuevas_disponibilidades(disponibilidades_data)
            
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

    def _validar_overlap_nuevas_disponibilidades(self, disponibilidades_data):
        """Valida que no haya solapamiento entre las nuevas disponibilidades del MISMO prestador."""
        from apps.turnos_core.models import Lugar
        
        # Validar overlap entre las nuevas disponibilidades
        for i, disp1 in enumerate(disponibilidades_data):
            for j, disp2 in enumerate(disponibilidades_data[i+1:], i+1):
                # Validar solapamiento en el mismo día (sin importar la sede)
                if disp1["dia_semana"] == disp2["dia_semana"]:
                    
                    # Verificar solapamiento
                    if self._hay_solapamiento_disponibilidades(disp1, disp2):
                        lugar1 = Lugar.objects.get(id=disp1["lugar"])
                        lugar2 = Lugar.objects.get(id=disp2["lugar"])
                        dia_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][disp1["dia_semana"]]
                        raise DRFValidationError(
                            f"El prestador no puede tener turnos solapados en {dia_nombre}. "
                            f"Los horarios {disp1['hora_inicio']}-{disp1['hora_fin']} en {lugar1.nombre} y "
                            f"{disp2['hora_inicio']}-{disp2['hora_fin']} en {lugar2.nombre} se superponen."
                        )

    def _validar_overlap_disponibilidades(self, prestador, disponibilidades_data):
        """Valida que no haya solapamiento entre las nuevas disponibilidades del MISMO prestador."""
        from apps.turnos_core.models import Lugar, Disponibilidad
        
        # 1. Validar overlap entre las nuevas disponibilidades
        for i, disp1 in enumerate(disponibilidades_data):
            for j, disp2 in enumerate(disponibilidades_data[i+1:], i+1):
                # Validar solapamiento en el mismo día (sin importar la sede)
                if disp1["dia_semana"] == disp2["dia_semana"]:
                    
                    # Verificar solapamiento
                    if self._hay_solapamiento_disponibilidades(disp1, disp2):
                        lugar1 = Lugar.objects.get(id=disp1["lugar"])
                        lugar2 = Lugar.objects.get(id=disp2["lugar"])
                        dia_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][disp1["dia_semana"]]
                        raise DRFValidationError(
                            f"El prestador no puede tener turnos solapados en {dia_nombre}. "
                            f"Los horarios {disp1['hora_inicio']}-{disp1['hora_fin']} en {lugar1.nombre} y "
                            f"{disp2['hora_inicio']}-{disp2['hora_fin']} en {lugar2.nombre} se superponen."
                        )
        
        # 2. Validar overlap con disponibilidades existentes del MISMO prestador (solo si es update)
        if prestador and hasattr(prestador, 'id') and prestador.id:
            for disp_nueva in disponibilidades_data:
                # Validar rango válido
                i = _to_time(disp_nueva["hora_inicio"])
                f = _to_time(disp_nueva["hora_fin"])
                if not i < f:
                    raise DRFValidationError(
                        f"Rango inválido {disp_nueva['hora_inicio']}-{disp_nueva['hora_fin']}: "
                        "hora_inicio debe ser menor que hora_fin."
                    )
                
                # Buscar disponibilidades existentes del MISMO prestador, mismo día (sin importar sede)
                disponibilidades_existentes = Disponibilidad.objects.filter(
                    prestador=prestador,
                    dia_semana=disp_nueva["dia_semana"],
                    activo=True
                )
                
                for disp_existente in disponibilidades_existentes:
                    if self._hay_solapamiento_horarios(
                        disp_nueva["hora_inicio"], disp_nueva["hora_fin"],
                        disp_existente.hora_inicio, disp_existente.hora_fin
                    ):
                        lugar_nueva = Lugar.objects.get(id=disp_nueva["lugar"])
                        lugar_existente = Lugar.objects.get(id=disp_existente.lugar_id)
                        dia_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][disp_nueva["dia_semana"]]
                        raise DRFValidationError(
                            f"El prestador ya tiene una disponibilidad en {dia_nombre} "
                            f"que se solapa con el horario {disp_nueva['hora_inicio']}-{disp_nueva['hora_fin']} en {lugar_nueva.nombre}. "
                            f"Horario existente: {disp_existente.hora_inicio}-{disp_existente.hora_fin} en {lugar_existente.nombre}"
                        )

    def _hay_solapamiento_disponibilidades(self, disp1, disp2):
        """Verifica si dos disponibilidades se solapan (payload vs payload)."""
        return _rango_solapa(
            disp1["hora_inicio"], disp1["hora_fin"],
            disp2["hora_inicio"], disp2["hora_fin"],
        )

    def _hay_solapamiento_horarios(self, inicio1, fin1, inicio2, fin2):
        """Verifica si dos rangos de tiempo se solapan (payload vs BD)."""
        return _rango_solapa(inicio1, fin1, inicio2, fin2)


# ------------------------------------------------------------------------------
# CrearTurnoBonificadoSerializer
# - Propósito: emisión manual de bonificaciones (vouchers) por admin.
# - Input: usuario_id, tipo_turno (x1..x4 o alias), motivo?, valido_hasta?.
# - Validaciones: usuario existe; mapeo de alias a code x1..x4.
# - create(): llama emitir_bonificacion_manual (service) con admin actual en context.
# ------------------------------------------------------------------------------

class CrearTurnoBonificadoSerializer(serializers.Serializer):
    # Requeridos
    usuario_id = serializers.IntegerField()
    sede_id = serializers.IntegerField()
    tipo_clase_id = serializers.IntegerField()

    # Opcionales
    motivo = serializers.CharField(required=False, allow_blank=True)
    valido_hasta = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        request = self.context["request"]
        admin = request.user

        # Usuario destino
        try:
            usuario = Usuario.objects.only("id", "cliente_id").get(pk=attrs["usuario_id"])
        except ObjectDoesNotExist:
            raise serializers.ValidationError({"usuario_id": "Usuario no encontrado."})

        # Sede (Lugar)
        try:
            sede = Lugar.objects.only("id", "cliente_id").get(pk=attrs["sede_id"])
        except ObjectDoesNotExist:
            raise serializers.ValidationError({"sede_id": "Sede (Lugar) no encontrada."})

        # Multi-tenant básico
        sede_cliente_id = getattr(sede, "cliente_id", None)
        
        # Verificar permisos del admin
        if not admin.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual == "admin_cliente":
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual or sede_cliente_id != cliente_actual.id:
                    raise serializers.ValidationError("No autorizado a operar sobre esta sede.")
            elif rol_actual not in ["super_admin", "admin_cliente"]:
                raise serializers.ValidationError("No autorizado a crear bonificaciones.")
        
        # Verificar que el usuario pertenece al cliente de la sede
        if hasattr(usuario, "cliente_id") and usuario.cliente_id != sede_cliente_id:
            raise serializers.ValidationError("El usuario no pertenece al cliente de la sede.")

        # Tipo de clase (activo) y pertenencia a la sede
        try:
            tc = (
                TipoClasePadel.objects
                .select_related("configuracion_sede__sede")
                .only("id", "codigo", "precio", "activo", "configuracion_sede__sede_id")
                .get(pk=attrs["tipo_clase_id"], activo=True)
            )
        except ObjectDoesNotExist:
            raise serializers.ValidationError({"tipo_clase_id": "Tipo de clase inexistente o inactivo."})

        if tc.configuracion_sede.sede_id != sede.id:
            raise serializers.ValidationError("El tipo de clase no pertenece a la sede indicada.")

        # Guardar instancias para create()
        attrs["_admin"] = admin
        attrs["_usuario"] = usuario
        attrs["_sede"] = sede
        attrs["_tc"] = tc
        return attrs

    def create(self, validated_data):
        admin = validated_data["_admin"]
        usuario = validated_data["_usuario"]
        sede = validated_data["_sede"]
        tc = validated_data["_tc"]

        motivo = validated_data.get("motivo") or "Bonificación manual"
        valido_hasta = validated_data.get("valido_hasta")

        bono = emitir_bonificacion_manual(
            admin_user=admin,
            usuario=usuario,
            sede=sede,                 # requerido por la nueva firma
            tipo_clase_id=tc.id,       # requerido por la nueva firma
            motivo=motivo,
            valido_hasta=valido_hasta,
        )

        logger.info(
            "[BONIFICACION][manual][api] admin=%s user=%s sede=%s tipo_clase_id=%s bono=%s valor=%s",
            getattr(admin, "id", None),
            getattr(usuario, "id", None),
            getattr(sede, "id", None),
            tc.id,
            getattr(bono, "id", None),
            getattr(bono, "valor", None),
        )
        return bono

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




class ToggleReservadoParaAbonoSerializer(serializers.Serializer):
    turno_id = serializers.IntegerField()
    reservado_para_abono = serializers.BooleanField()