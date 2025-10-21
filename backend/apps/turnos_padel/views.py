# apps/turnos_padel/views.py
from rest_framework import viewsets, status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.response import Response 
from apps.common.permissions import (
    EsAdminDeSuCliente,
    EsSuperAdmin,
    SoloLecturaUsuariosFinalesYEmpleados
)

from rest_framework import serializers

from apps.turnos_core.models import Lugar, Turno, TurnoBonificado
from apps.turnos_padel.models import ConfiguracionSedePadel, TipoClasePadel, AbonoMes, TipoAbonoPadel
from apps.turnos_padel.serializers import (
    SedePadelSerializer,
    ConfiguracionSedePadelSerializer,
    TipoClasePadelSerializer,
    AbonoMesSerializer,
    AbonoMesDetailSerializer,
    TipoAbonoPadelSerializer
)

from django.db import transaction
from calendar import Calendar
from django.utils import timezone 
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Max


from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from rest_framework.request import Request
from rest_framework.parsers import JSONParser
from io import BytesIO
import json
from apps.turnos_padel.services.abonos import confirmar_y_reservar_abono
from apps.turnos_padel.services.abonos import validar_y_confirmar_abono, _notify_abono_admin


from datetime import date, timedelta
from django.utils.dateparse import parse_date
from django.db.models import Count


import logging
from django.db.models import Max 
logger = logging.getLogger(__name__)


DSEM = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

class SedePadelViewSet(viewsets.ModelViewSet):
    """
    CRUD de sedes con configuración y tipos embebidos.
    - Autenticación JWT.
    - Permisos: admins del cliente y superadmins; lectura para usuarios/empleados.
    - get_queryset restringe por cliente (multi-tenant seguro).
    - list/retrieve garantizan existencia de Configuración y catálogos base (x1..x4).
      ⚠️ Efecto colateral deliberado: autocrea entidades faltantes al consultar.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin | SoloLecturaUsuariosFinalesYEmpleados]
    serializer_class = SedePadelSerializer

    def get_queryset(self):
        # ✅ Restringe por tipo de usuario y cliente; usa select_related/prefetch para evitar N+1.
        user = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)

        # Super admin: si hay tenant resuelto, filtrar por ese cliente; si no, ver todo
        if user.is_super_admin:
            base = Lugar.objects.all()
            if cliente_actual is not None:
                base = base.filter(cliente=cliente_actual)
            return (
                base
                .select_related("configuracion_padel")
                .prefetch_related("configuracion_padel__tipos_clase")
            )
        # Admin del cliente → sedes de su cliente
        if cliente_actual is not None:
            return (
                Lugar.objects.filter(cliente=cliente_actual)
                .select_related("configuracion_padel")
                .prefetch_related("configuracion_padel__tipos_clase")
            )
        return Lugar.objects.none()

    def list(self, request, *args, **kwargs):
        # 🛡️ Side-effect: asegura config y catálogos por sede al listar.
        #    Útil para DX, pero considerar mover a signal/post_save si se requiere pureza REST.
        queryset = self.get_queryset()
        for sede in queryset:
            config, created = ConfiguracionSedePadel.objects.get_or_create(
                sede=sede, defaults={"alias": "", "cbu_cvu": ""}
            )
            if created:
                # Catálogo default de tipos clase y tipos de abono
                for codigo in ["x1", "x2", "x3", "x4"]:
                    TipoClasePadel.objects.create(configuracion_sede=config, codigo=codigo, precio=0, activo=True)
                for codigo in ["x1", "x2", "x3", "x4"]:
                    TipoAbonoPadel.objects.create(configuracion_sede=config, codigo=codigo, precio=0, activo=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        # ♻️ Misma garantía que en list() para una sede específica.
        instance = self.get_object()
        config, created = ConfiguracionSedePadel.objects.get_or_create(
            sede=instance, defaults={"alias": "", "cbu_cvu": ""}
        )
        if created:
            for codigo in ["x1", "x2", "x3", "x4"]:
                TipoClasePadel.objects.create(configuracion_sede=config, codigo=codigo, precio=0, activo=True)
            for codigo in ["x1", "x2", "x3", "x4"]:
                TipoAbonoPadel.objects.create(configuracion_sede=config, codigo=codigo, precio=0, activo=True)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @transaction.atomic
    def perform_create(self, serializer):
        # 🧾 Asigna cliente desde el cliente actual (consistencia multi-tenant).
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        if cliente_actual:
            return serializer.save(cliente=cliente_actual)
        else:
            raise ValueError("No se puede crear sede sin cliente actual")

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # ✅ Update atómico y validado; soporta PATCH vía partial.
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class ConfiguracionSedePadelViewSet(viewsets.ModelViewSet):
    """
    CRUD de configuraciones de sede pádel.
    - lookup_field por 'sede_id' (DX para frontend).
    - Filtro por cliente en get_queryset (seguridad multi-tenant).
    - get_object obtiene por sede_id y responde 404 si no existe.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin | SoloLecturaUsuariosFinalesYEmpleados]
    serializer_class = ConfiguracionSedePadelSerializer
    lookup_field = "sede_id"  # Buscaremos por sede_id, no por id de configuración

    def get_queryset(self):
        user = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        qs = ConfiguracionSedePadel.objects.all()

        # Super admin (usar nuevo campo)
        if user.is_super_admin:
            return qs
        # Admin del cliente → configuraciones de su cliente
        elif cliente_actual:
            qs = qs.filter(sede__cliente=cliente_actual)
        else:
            return ConfiguracionSedePadel.objects.none()

        return qs

    def get_object(self):
        # 🔎 Error explícito si la sede no tiene configuración cargada.
        sede_id = self.kwargs.get(self.lookup_field)
        try:
            return ConfiguracionSedePadel.objects.get(sede_id=sede_id)
        except ConfiguracionSedePadel.DoesNotExist:
            raise NotFound(f"La sede con ID {sede_id} no tiene configuración de pádel.")

class TipoClasePadelViewSet(viewsets.ModelViewSet):
    """
    CRUD para tipos de clase (p. ej., actualización de precios).
    - Filtro por cliente y por sede_id via query params.
    - Usa only/select_related implícitos vía relations del serializer según necesidad.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin | SoloLecturaUsuariosFinalesYEmpleados]
    serializer_class = TipoClasePadelSerializer

    def get_queryset(self):
        user = self.request.user
        sede_id = self.request.query_params.get("sede_id")

        qs = TipoClasePadel.objects.all()

        # 🔹 Restringir por cliente (si aplica). Evita fuga de datos entre tenants.
        if hasattr(user, "cliente"):
            qs = qs.filter(configuracion_sede__sede__cliente=user.cliente)

        # 🔹 Filtrar por sede (opcional).
        if sede_id:
            qs = qs.filter(configuracion_sede__sede_id=sede_id)

        return qs

def _week_bounds(d: date):
    # Lunes a Domingo (ISO)
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=6)
    return start, end


class AbonoMesViewSet(viewsets.ModelViewSet):
    """
    Gestión de AbonoMes.
    - Autenticación JWT; permiso mínimo IsAuthenticated.
    - get_queryset respeta el alcance: super_admin (todo), admin_cliente (por cliente), usuario_final (los propios).
    - create/reservar: validación + confirmación + reserva en un único paso (transaccional),
      soporta bonificaciones y archivo de comprobante; notifica admins del cliente.
    - Endpoint adicionales:
        * GET /abonos/disponibles: consulta horas disponibles (consistencia en todo el mes actual + siguiente).
        * POST /abonos/reservar: alias de create con misma lógica (DX frontend).
    - Logging informativo y de advertencia para trazabilidad.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _as_bool(val) -> bool:
        # 🔎 Normaliza flags booleanos recibidos como strings/enteros.
        if val is True:
            return True
        if val is False or val is None:
            return False
        return str(val).strip().lower() in ("1", "true", "t", "yes", "y", "on")

    def get_queryset(self):
        # 🧭 Scope por perfil; logs con contexto mínimo (id/tipo).
        user = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Importar y usar la función helper
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(self.request)
        
        logger.info("[AbonoMesViewSet:get_queryset] Usuario: %s rol_actual: %s", user.id, rol_actual)

        # Super admin (usar nuevo campo)
        if user.is_super_admin:
            qs = AbonoMes.objects.all()
        # Admin del cliente → TODOS los abonos de su cliente (incluyendo los suyos)
        elif rol_actual == "admin_cliente" and cliente_actual:
            qs = AbonoMes.objects.filter(sede__cliente_id=cliente_actual.id)
        # Usuario final → sus propios abonos DEL CLIENTE ACTUAL
        else:
            if cliente_actual:
                qs = AbonoMes.objects.filter(usuario=user, sede__cliente_id=cliente_actual.id)
            else:
                qs = AbonoMes.objects.filter(usuario=user)
        
        # Aplicar filtros por parámetros de query
        prestador_id = self.request.query_params.get('prestador_id')
        if prestador_id:
            try:
                qs = qs.filter(prestador_id=int(prestador_id))
            except (ValueError, TypeError):
                pass
        
        sede_id = self.request.query_params.get('sede_id')
        if sede_id:
            try:
                qs = qs.filter(sede_id=int(sede_id))
            except (ValueError, TypeError):
                pass
        
        return qs

    def get_serializer_class(self):
        # 📄 Detail y list retornan versión enriquecida; create/update usan base.
        if self.action in ["retrieve", "list"]:
            return AbonoMesDetailSerializer
        return AbonoMesSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # 🧾 Crea/valida/confirmar en un único paso; respeta multi-tenant y roles.
        user = request.user
        logger.info("[AbonoMesViewSet:create] Usuario: %s (%s)", user.id, user.tipo_usuario)
        logger.debug("[AbonoMesViewSet:create] Data original: %s", request.data)

        data = request.data.copy()

        # ➜ Acepta 'usuario' o 'usuario_id' y valida alcance según rol.
        usuario_target = data.get("usuario") or data.get("usuario_id")
        
        # Importar y usar la función helper
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        if rol_actual == "usuario_final":
            if usuario_target and int(usuario_target) != user.id:
                return Response({"detail": "No podés crear abonos para otro usuario."}, status=403)
            data["usuario"] = user.id
        else:
            if not usuario_target:
                return Response({"detail": "Debe indicar usuario para asignar el abono."}, status=400)
            try:
                data["usuario"] = int(usuario_target)
            except (TypeError, ValueError):
                return Response({"detail": "Usuario inválido."}, status=400)

            # Validación de sede y pertenencia a cliente (admin_cliente).
            try:
                sede_id = int(data.get("sede"))
            except (TypeError, ValueError):
                return Response({"detail": "Sede inválida."}, status=400)

            from django.contrib.auth import get_user_model
            Usuario = get_user_model()
            target_user = Usuario.objects.only("id", "cliente_id").filter(id=data["usuario"]).first()
            if not target_user:
                return Response({"detail": "Usuario destino inexistente."}, status=404)

            try:
                sede = Lugar.objects.only("id", "cliente_id").get(id=sede_id)
            except Lugar.DoesNotExist:
                return Response({"detail": "Sede no encontrada."}, status=404)

            if not user.is_super_admin:
                from apps.auth_core.utils import get_rol_actual_del_jwt
                rol_actual = get_rol_actual_del_jwt(request)
                
                if rol_actual == "admin_cliente":
                    cliente_actual = getattr(request, 'cliente_actual', None)
                    if not cliente_actual or target_user.cliente_id != cliente_actual.id or sede.cliente_id != cliente_actual.id:
                        logger.warning(
                            "[abonos.create][cliente_mismatch] admin=%s target_user=%s sede=%s",
                            user.id, target_user.id, sede.id
                        )
                        return Response({"detail": "No autorizado para asignar fuera de tu cliente."}, status=403)

        # Flag administrativo para omitir comprobante (controlado por rol arriba).
        forzar_admin = self._as_bool(data.get("forzar_admin"))

        # Bonificaciones y archivo (FormData soportado).
        bonificaciones_ids = data.getlist("bonificaciones_ids") if hasattr(data, "getlist") else data.get("bonificaciones_ids", [])
        archivo = data.get("archivo")

        # ✅ Validar y confirmar abono (service centraliza reglas e idempotencia).
        try:
            abono, resumen = validar_y_confirmar_abono(
                data=data,
                bonificaciones_ids=bonificaciones_ids,
                archivo=archivo,
                request=request,
                forzar_admin=forzar_admin,  # 👈
            )
        except serializers.ValidationError as e:
            return Response(e.detail, status=400)

        resp_serializer = self.get_serializer(abono)
        payload = resp_serializer.data
        payload["resumen"] = resumen
        payload["monto_sugerido"] = resumen.get("monto_sugerido")

        # 🔔 Notifica a admins del cliente de la sede (excluye super_admin).
        try:
            from apps.notificaciones_core.services import publish_event, notify_inapp, TYPE_RESERVA_ABONO
            from django.contrib.auth import get_user_model

            Usuario = get_user_model()
            cliente_id = getattr(abono.sede, "cliente_id", None)  # 🔑 clave para el scope de admins

            DSEM = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            sede_nombre = getattr(abono.sede, "nombre", None)
            prestador_nombre = getattr(abono.prestador, "nombre_publico", None)
            hora_txt = str(abono.hora)[:5]
            dia_semana_text = DSEM[abono.dia_semana] if 0 <= abono.dia_semana <= 6 else ""

            ev = publish_event(
                topic="abonos.reserva_confirmada",
                actor=request.user,
                cliente_id=cliente_id,
                metadata={
                    "abono_id": abono.id,
                    "usuario": getattr(abono.usuario, "email", None),
                    "sede_id": getattr(abono.sede, "id", None),
                    "prestador_id": getattr(abono.prestador, "id", None),
                    "anio": abono.anio, "mes": abono.mes, "dia_semana": abono.dia_semana,
                    "hora": hora_txt,
                    "tipo": getattr(abono.tipo_clase, "codigo", None),
                    "monto": abono.monto,
                },
            )

            admins = Usuario.objects.filter(
                cliente_id=cliente_id,
                tipo_usuario="admin_cliente"
            ).only("id", "cliente_id")

            ctx = {
                a.id: {
                    "abono_id": abono.id,
                    "usuario": getattr(abono.usuario, "email", None),
                    "tipo": getattr(abono.tipo_clase, "codigo", None),
                    "sede_nombre": sede_nombre,
                    "prestador": prestador_nombre,
                    "hora": hora_txt,
                    "dia_semana_text": dia_semana_text,
                    "reservados_mes_actual": resumen.get("reservados_mes_actual", 0),
                    "prioridad_mes_siguiente": resumen.get("prioridad_mes_siguiente", 0),
                } for a in admins
            }

            notify_inapp(
                event=ev,
                recipients=admins,
                notif_type=TYPE_RESERVA_ABONO,
                context_by_user=ctx,
                severity="info",
            )
            logger.info("[abonos.notif] create -> admins=%s", admins.count())

            # -------- Notificación al usuario --------
            from apps.notificaciones_core.services import TYPE_RESERVA_ABONO_USER
            
            ev_user = publish_event(
                topic="abonos.reserva_confirmada.usuario",
                actor=request.user,
                cliente_id=cliente_id,
                metadata={
                    "abono_id": abono.id,
                    "usuario": getattr(abono.usuario, "email", None),
                    "sede_id": getattr(abono.sede, "id", None),
                    "prestador_id": getattr(abono.prestador, "id", None),
                    "anio": abono.anio, "mes": abono.mes, "dia_semana": abono.dia_semana,
                    "hora": hora_txt,
                    "tipo": getattr(abono.tipo_clase, "codigo", None),
                    "monto": abono.monto,
                },
            )

            ctx_user = {
                abono.usuario.id: {
                    "abono_id": abono.id,
                    "tipo": getattr(abono.tipo_clase, "codigo", None),
                    "sede_nombre": sede_nombre,
                    "prestador": prestador_nombre,
                    "hora": hora_txt,
                    "dia_semana_text": dia_semana_text,
                    "mes_anio": f"{str(abono.mes).zfill(2)}/{abono.anio}",
                }
            }

            notify_inapp(
                event=ev_user,
                recipients=[abono.usuario],
                notif_type=TYPE_RESERVA_ABONO_USER,
                context_by_user=ctx_user,
                severity="info",
            )
            logger.info("[abonos.notif] create -> user=%s", abono.usuario.id)

        except Exception:
            # 🧯 No rompe la transacción del abono si falla la notificación (log con stack).
            logger.exception("[notif][abono_reserva][fail]")

        logger.info("[AbonoMesViewSet:create] Abono creado y reservado correctamente")
        return Response(payload, status=201)

    @action(detail=False, methods=["GET"], url_path="disponibles")
    def disponibles(self, request):
        """
        Devuelve horas que están libres en TODAS las fechas del patrón (mes actual >= hoy + mes siguiente).
        - Autorización por sede/cliente.
        - Opcionales: hora específica y tipo_codigo para combinar con catálogo activo.
        - Evita horas con turnos bloqueados/ya reservados/estado != disponible.
        """
        logger.info("[abonos.disponibles] params=%s", dict(request.query_params))
        try:
            sede_id = int(request.query_params.get("sede_id"))
            prestador_id = int(request.query_params.get("prestador_id"))
            dia_semana = int(request.query_params.get("dia_semana"))  # 0..6
            anio = int(request.query_params.get("anio"))
            mes = int(request.query_params.get("mes"))
        except (TypeError, ValueError):
            logger.warning("[abonos.disponibles] Parámetros inválidos")
            return Response({"detail": "Parámetros inválidos"}, status=status.HTTP_400_BAD_REQUEST)

        hora_filtro = request.query_params.get("hora")        # opcional

        # 🔐 Autorización por cliente/sede (multi-tenant).
        sede = Lugar.objects.select_related("cliente").filter(id=sede_id).first()
        if not sede:
            return Response({"detail": "Sede no encontrada"}, status=404)

        user = request.user
        if not user.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual == "admin_cliente":
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual or sede.cliente_id != cliente_actual.id:
                    return Response({"detail": "No autorizado para esta sede"}, status=403)
            elif rol_actual not in ("super_admin", "admin_cliente"):
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual or cliente_actual.id != sede.cliente_id:
                    return Response({"detail": "No autorizado"}, status=403)

        # 1) Catálogo de tipos de clase activos (ya no se filtra por código).
        tipos_qs = TipoClasePadel.objects.filter(
            configuracion_sede__sede_id=sede_id,
            activo=True
        ).only("id", "codigo", "precio")

        tipos_map = [{
            "id": t.id,
            "codigo": t.codigo,
            "nombre": t.get_codigo_display(),
            "precio": t.precio,
        } for t in tipos_qs]

        # 2) Construcción de fechas: resto del mes actual (>= hoy) + todo el próximo mes para el día de semana.
        def fechas_mes(anio_i, mes_i, dsem):
            cal = Calendar(firstweekday=0)  # 0 = lunes
            out = []
            for week in cal.monthdatescalendar(anio_i, mes_i):
                for d in week:
                    if d.month == mes_i and d.weekday() == dsem:
                        out.append(d)
            return out

        def proximo_mes(anio_i, mes_i):
            return (anio_i + 1, 1) if mes_i == 12 else (anio_i, mes_i + 1)

        hoy = timezone.localdate()
        ahora = timezone.now()
        fechas_turnos_abono = fechas_mes(anio, mes, dia_semana)
        
        # Solo fechas del mes actual con lógica de anticipación
        HORAS_ANTICIPACION_MINIMA = 1
        fechas_turnos_abono_futuras = []
        for fecha in fechas_turnos_abono:
            if fecha > hoy:
                # Fechas futuras del mes actual: incluir todas
                fechas_turnos_abono_futuras.append(fecha)
            elif fecha == hoy:
                # Día actual: verificar anticipación mínima
                hora_actual = ahora.hour
                # Solo restringir si ya pasó la hora límite (23:00 para 1h de anticipación)
                if hora_actual < (24 - HORAS_ANTICIPACION_MINIMA):
                    fechas_turnos_abono_futuras.append(fecha)

        # Validar que hay al menos una fecha disponible en el mes actual
        if not fechas_turnos_abono_futuras:
            logger.info("[abonos.disponibles] sin fechas disponibles en el mes actual para el día de semana")
            return Response([], status=200)

        # Solo usar las fechas futuras del mes actual, NO el próximo mes
        fechas_total = fechas_turnos_abono_futuras
        logger.debug(
            "[abonos.disponibles] hoy=%s | fechas_turnos_abono_futuras=%s | total=%s",
            hoy, len(fechas_turnos_abono_futuras), len(fechas_total)
        )

        # 3) Recupera turnos para todas las fechas; agrupa por hora.
        try:
            ct_prestador = ContentType.objects.get(app_label="turnos_core", model="prestador")
        except ContentType.DoesNotExist:
            logger.error("[abonos.disponibles] ContentType prestador no encontrado")
            return Response({"detail": "Error de configuración (prestador)"}, status=500)

        base_q = Q(lugar_id=sede_id) & Q(content_type=ct_prestador, object_id=prestador_id) & Q(fecha__in=fechas_total)

        turnos_qs = Turno.objects.filter(base_q).only(
            "id", "fecha", "hora", "estado",
            "abono_mes_reservado", "abono_mes_prioridad", "lugar_id"
        )
        if hora_filtro:
            turnos_qs = turnos_qs.filter(hora=hora_filtro)

        por_hora = {}
        for t in turnos_qs:
            h = t.hora.isoformat()
            por_hora.setdefault(h, {})[t.fecha] = t

        # 4) Una hora es válida si TODAS las fechas del patrón están libres/no bloqueadas/no asignadas a abonos.
        horas_libres = []
        for h, mapa in por_hora.items():
            if not all(f in mapa for f in fechas_total):
                continue
            ok = True
            for f in fechas_total:
                t = mapa[f]
                if t.estado != "disponible":
                    ok = False; break
                if getattr(t, "abono_mes_reservado", False) or getattr(t, "abono_mes_prioridad", False):
                    ok = False; break
                if hasattr(t, "bloqueado_para_reservas") and getattr(t, "bloqueado_para_reservas", False):
                    ok = False; break
            if ok:
                horas_libres.append(h)

        # Filtrar horas para el día actual (solo si hay fechas del día actual)
        if hoy in fechas_total:
            # Usar la zona horaria local en lugar de UTC
            import pytz
            local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
            ahora_local = ahora.astimezone(local_tz)
            hora_actual = ahora_local.hour
            hora_minima = hora_actual + HORAS_ANTICIPACION_MINIMA
            
            # Filtrar horas que estén a más de 1 hora de la hora actual
            horas_libres_filtradas = []
            for h in horas_libres:
                hora_turno = int(h.split(':')[0])  # Extraer la hora (ej: "09:00:00" -> 9)
                if hora_turno >= hora_minima:
                    horas_libres_filtradas.append(h)
            
            horas_libres = horas_libres_filtradas

        horas_libres.sort()
        result = [{"hora": h} for h in horas_libres]

        logger.info(
            "[abonos.disponibles] sede=%s prestador=%s dsem=%s anio=%s mes=%s -> horas=%s",
            sede_id, prestador_id, dia_semana, anio, mes, horas_libres
        )
        return Response(result, status=200)

    @action(detail=False, methods=["post"], url_path="reservar")
    @transaction.atomic
    def reservar(self, request):
        """
        Alias de creación para reservar abonos en un solo paso.
        - Misma validación de alcance que create().
        - Adjunta bonificaciones/archivo y notifica admins del cliente.
        - Transacción atómica para consistencia.
        """
        logger.info("[abonos.reservar][inicio] request.data=%s", request.data)
        user = request.user
        data = request.data.copy()

        # ➜ Normaliza/valida usuario objetivo según rol (igual que create()).
        usuario_target = data.get("usuario") or data.get("usuario_id")
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        if rol_actual == "usuario_final":
            if usuario_target and int(usuario_target) != user.id:
                return Response({"detail": "No podés crear abonos para otro usuario."}, status=403)
            data["usuario"] = user.id
        else:
            if not usuario_target:
                return Response({"detail": "Debe indicar usuario para asignar el abono."}, status=400)
            try:
                data["usuario"] = int(usuario_target)
            except (TypeError, ValueError):
                return Response({"detail": "Usuario inválido."}, status=400)

            try:
                sede_id = int(data.get("sede"))
            except (TypeError, ValueError):
                return Response({"detail": "Sede inválida."}, status=400)

            from django.contrib.auth import get_user_model
            Usuario = get_user_model()
            target_user = Usuario.objects.only("id", "cliente_id").filter(id=data["usuario"]).first()
            if not target_user:
                return Response({"detail": "Usuario destino inexistente."}, status=404)

            try:
                sede = Lugar.objects.only("id", "cliente_id").get(id=sede_id)
            except Lugar.DoesNotExist:
                return Response({"detail": "Sede no encontrada."}, status=404)

            if not user.is_super_admin:
                from apps.auth_core.utils import get_rol_actual_del_jwt
                rol_actual = get_rol_actual_del_jwt(request)
                
                if rol_actual == "admin_cliente":
                    cliente_actual = getattr(request, 'cliente_actual', None)
                    if not cliente_actual or target_user.cliente_id != cliente_actual.id or sede.cliente_id != cliente_actual.id:
                        logger.warning(
                            "[abonos.reservar][cliente_mismatch] admin=%s target_user=%s sede=%s",
                            user.id, target_user.id, sede.id
                        )
                        return Response({"detail": "No autorizado para asignar fuera de tu cliente."}, status=403)

        # Flag administrativo opcional.
        forzar_admin = self._as_bool(data.get("forzar_admin"))

        bonificaciones_ids = data.getlist("bonificaciones_ids") if hasattr(data, "getlist") else data.get("bonificaciones_ids", [])
        archivo = data.get("archivo")

        logger.info("[abonos.reservar][payload] data=%s bonificaciones_ids=%s tiene_archivo=%s", 
                   data, bonificaciones_ids, bool(archivo))

        logger.info("[abonos.reservar][call] llamando validar_y_confirmar_abono con data=%s bonificaciones_ids=%s forzar_admin=%s", 
                   data, bonificaciones_ids, forzar_admin)

        try:
            abono, resumen = validar_y_confirmar_abono(
                data=data,
                bonificaciones_ids=bonificaciones_ids,
                archivo=archivo,
                request=request,
                forzar_admin=forzar_admin,  # 👈
            )
        except serializers.ValidationError as e:
            return Response(e.detail, status=400)

        serializer = self.get_serializer(abono)
        payload = serializer.data
        payload["resumen"] = resumen
        payload["monto_sugerido"] = resumen.get("monto_sugerido")

        # 🔔 Notificación a admins (idéntica a create()).
        try:
            from apps.notificaciones_core.services import publish_event, notify_inapp, TYPE_RESERVA_ABONO
            from django.contrib.auth import get_user_model

            Usuario = get_user_model()
            cliente_id = getattr(abono.sede, "cliente_id", None)

            
            sede_nombre = getattr(abono.sede, "nombre", None)
            prestador_nombre = getattr(abono.prestador, "nombre_publico", None)
            hora_txt = str(abono.hora)[:5]
            dia_semana_text = DSEM[abono.dia_semana] if 0 <= abono.dia_semana <= 6 else ""

            ev = publish_event(
                topic="abonos.reserva_confirmada",
                actor=request.user,
                cliente_id=cliente_id,
                metadata={
                    "abono_id": abono.id,
                    "usuario": getattr(abono.usuario, "email", None),
                    "sede_id": getattr(abono.sede, "id", None),
                    "prestador_id": getattr(abono.prestador, "id", None),
                    "anio": abono.anio, "mes": abono.mes, "dia_semana": abono.dia_semana,
                    "hora": hora_txt,
                    "tipo": getattr(abono.tipo_clase, "codigo", None),
                    "monto": abono.monto,
                },
            )

            admins = Usuario.objects.filter(
                cliente_id=cliente_id,
                tipo_usuario="admin_cliente"
            ).only("id", "cliente_id")

            ctx = {
                a.id: {
                    "abono_id": abono.id,
                    "usuario": getattr(abono.usuario, "email", None),
                    "tipo": getattr(abono.tipo_clase, "codigo", None),
                    "sede_nombre": sede_nombre,
                    "prestador": prestador_nombre,
                    "hora": hora_txt,
                    "dia_semana_text": dia_semana_text,
                    "reservados_mes_actual": resumen.get("reservados_mes_actual", 0),
                    "prioridad_mes_siguiente": resumen.get("prioridad_mes_siguiente", 0),
                } for a in admins
            }

            notify_inapp(
                event=ev,
                recipients=admins,
                notif_type=TYPE_RESERVA_ABONO,
                context_by_user=ctx,
                severity="info",
            )
            logger.info("[abonos.notif] reservar -> admins=%s", admins.count())
        except Exception:
            logger.exception("[notif][abono_reserva][fail]")

        return Response(payload, status=201)
    
    @action(detail=False, methods=["GET"], url_path="mios")
    def mios(self, request):
        """
        Lista de mis abonos (o de un usuario si admin pasa ?usuario_id=).
        Incluye último turno, ventana_renovacion, estado_vigencia y
        datos de día/hora para la UI.
        """
        user = request.user
        qs = self.get_queryset()

        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        if rol_actual == "usuario_final":
            qs = qs.filter(usuario=user)
        else:
            uid = request.query_params.get("usuario_id")
            if uid:
                qs = qs.filter(usuario_id=uid)

        hoy = timezone.localdate()
        data = []
        for a in qs.select_related("sede", "prestador", "tipo_clase").prefetch_related("turnos_reservados"):
            ult = a.turnos_reservados.aggregate(ultimo=Max("fecha"))["ultimo"]
            dias = (ult - hoy).days if ult else None
            estado_vigencia = "activo" if ult and hoy <= ult else "vencido"
            ventana_renovacion = bool(dias is not None and 0 <= dias <= 7 and not a.renovado)

            # Obtener turnos reservados con información básica
            turnos_reservados = []
            for turno in a.turnos_reservados.all().order_by("fecha", "hora"):
                turnos_reservados.append({
                    "id": turno.id,
                    "fecha": turno.fecha.isoformat(),
                    "hora": turno.hora.isoformat(),
                    "lugar": getattr(turno.lugar, "nombre", None),
                    "estado": turno.estado
                })
            
            item = {
                "id": a.id,
                "sede_id": a.sede_id,
                "sede_nombre": getattr(a.sede, "nombre", None),
                "prestador_id": a.prestador_id,
                "prestador_nombre": getattr(a.prestador, "nombre_publico", None) or getattr(a.prestador, "nombre", None),
                "tipo_clase_id": a.tipo_clase_id,
                "tipo_clase_codigo": getattr(a.tipo_clase, "codigo", None),
                "tipo_clase_precio": getattr(a.tipo_clase, "precio", None) if a.tipo_clase else None,
                "anio": a.anio, 
                "mes": a.mes,
                "renovado": a.renovado,
                "vence_el": str(ult) if ult else None,
                "dias_para_vencer": dias,
                "ventana_renovacion": ventana_renovacion,
                "estado_vigencia": estado_vigencia,
                # 👇 claves para render "Lunes 10:00 hs"
                "dia_semana": a.dia_semana,
                "dia_semana_label": DSEM[a.dia_semana] if 0 <= a.dia_semana <= 6 else None,
                "hora": a.hora.isoformat() if a.hora else None,       # "10:00:00"
                "hora_text": a.hora.strftime("%H:%M") if a.hora else None,  # "10:00"
                # 👇 turnos reservados para el componente AbonosList
                "turnos_reservados": turnos_reservados
            }
            data.append(item)

        return Response(data, status=200)
    
    @action(detail=True, methods=["POST"], url_path="marcar-renovado")
    def marcar_renovado(self, request, pk=None):
        """
        Marca el abono como renovado (se usará luego por el cron).
        - usuario_final: sólo sobre sus propios abonos
        - admin_cliente/super_admin: sobre cualquier abono de su alcance
        """
        abono = self.get_object()
        user = request.user

        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        if rol_actual == "usuario_final" and abono.usuario_id != user.id:
            return Response({"detail": "No autorizado."}, status=403)

        abono.renovado = True
        abono.save(update_fields=["renovado"])

        # notif opcional (ya tenés helper importado)
        try:
            _notify_abono_admin(abono, actor=user, evento="renovado")
        except Exception:
            logger.exception("[abonos.marcar_renovado][notif][fail]")

        return Response({"ok": True, "renovado": True}, status=200)
    
    
    @action(detail=False, methods=["GET"], url_path="admin/resumen", permission_classes=[IsAuthenticated])
    def admin_resumen(self, request):
        """
        Resumen de abonos para admin:
        - granularity: day|week|month (default=day)
        - fecha: YYYY-MM-DD (default=hoy)
        - sede_id?, prestador_id?, usuario_id?
        - anio?, mes? (si granularity=month; si no vienen, toma de 'fecha')
        """
        user = request.user
        if user.is_super_admin:
            pass  # Super admin siempre tiene acceso
        else:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual not in ("super_admin", "admin_cliente"):
                return Response({"detail": "No autorizado."}, status=403)

        gran = (request.query_params.get("granularity") or "day").lower()
        fecha_str = request.query_params.get("fecha")
        hoy = timezone.localdate()
        base_date = parse_date(fecha_str) if fecha_str else hoy
        if not base_date:
            base_date = hoy

        sede_id = request.query_params.get("sede_id")
        prestador_id = request.query_params.get("prestador_id")
        usuario_id = request.query_params.get("usuario_id")

        qs = self.get_queryset()  # respeta alcance por rol
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        if prestador_id:
            qs = qs.filter(prestador_id=prestador_id)
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)

        # Ventana temporal
        if gran == "day":
            qs = qs.filter(anio=base_date.year, mes=base_date.month)
            # además, que coincida el día_semana y hora ese día:
            # el resumen diario se apoya en los turnos confirmados de ese mes
            ventana_label = base_date.isoformat()
        elif gran == "week":
            w_start, w_end = _week_bounds(base_date)
            qs = qs.filter(
                anio__in={w_start.year, w_end.year},  # por si cruza año
                mes__in={w_start.month, w_end.month}
            )
            ventana_label = f"{w_start.isoformat()}..{w_end.isoformat()}"
        else:  # month
            anio = int(request.query_params.get("anio") or base_date.year)
            mes = int(request.query_params.get("mes") or base_date.month)
            qs = qs.filter(anio=anio, mes=mes)
            ventana_label = f"{anio}-{mes:02d}"

        # Métricas básicas
        total = qs.count()
        por_estado = qs.values("estado").annotate(c=Count("id")).order_by()

        # Proyección rápida: próximos vencimientos (último turno reservado por abono)
        hoy = timezone.localdate()
        proximos = []
        for a in qs.select_related("sede", "prestador", "tipo_clase")[:200]:
            ult = a.turnos_reservados.aggregate(ultimo=Max("fecha"))["ultimo"]
            dias = (ult - hoy).days if ult else None
            if dias is not None and 0 <= dias <= 14:
                proximos.append({
                    "id": a.id,
                    "usuario_id": a.usuario_id,
                    "sede_id": a.sede_id,
                    "prestador_id": a.prestador_id,
                    "tipo": getattr(a.tipo_clase, "codigo", None),
                    "vence_el": str(ult),
                    "dias_para_vencer": dias,
                    "renovado": a.renovado,
                })

        payload = {
            "ventana": ventana_label,
            "filtros": {
                "sede_id": int(sede_id) if sede_id else None,
                "prestador_id": int(prestador_id) if prestador_id else None,
                "usuario_id": int(usuario_id) if usuario_id else None,
                "granularity": gran,
            },
            "totales": {
                "abonos": total,
                "por_estado": {row["estado"]: row["c"] for row in por_estado},
            },
            # opcional para UI: sample para panel (capado a 50)
            "items": [{
                "id": a.id,
                "usuario_id": a.usuario_id,
                "sede_id": a.sede_id,
                "prestador_id": a.prestador_id,
                "anio": a.anio, "mes": a.mes,
                "dia_semana": a.dia_semana,
                "hora": a.hora.strftime("%H:%M"),
                "tipo": getattr(a.tipo_clase, "codigo", None),
                "estado": a.estado,
            } for a in qs.select_related("tipo_clase")[:50]],
            "proximos_vencimientos": proximos[:50],
        }
        return Response(payload, status=200)

    @action(detail=True, methods=["post"], url_path="liberar", permission_classes=[IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)])
    @transaction.atomic
    def liberar(self, request, pk=None):
        """
        Libera vínculos de un AbonoMes.
        - Body:
            solo_prioridad: bool  (default: false)  → si true, sólo quita las "prioridades" del mes siguiente
            dry_run: bool         (default: true)   → si true, no modifica nada; sólo devuelve conteos
        - Efectos:
            * solo_prioridad=true:
                - Turno.abono_mes_prioridad = NULL
                - Turno.reservado_para_abono = False  (para que queden disponibles como clases sueltas)
            * solo_prioridad=false (liberación total):
                - Abono.estado = "cancelado"
                - Turno en turnos_reservados: usuario=NULL, estado="disponible", abono_mes_reservado=NULL
                - Turno en turnos_prioridad: abono_mes_prioridad=NULL, reservado_para_abono=False
                - Limpia M2M del abono
        """
        abono = self.get_object()

        # Tenancy para admin_cliente
        user = request.user
        if not user.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual == "admin_cliente":
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual or getattr(abono.sede, "cliente_id", None) != cliente_actual.id:
                    return Response({"detail": "No autorizado para este abono."}, status=403)

        # Flags
        def _as_bool_local(v):
            if v is True:
                return True
            if v in (False, None):
                return False
            return str(v).strip().lower() in ("1", "true", "t", "yes", "y", "on")

        solo_prioridad = _as_bool_local(request.data.get("solo_prioridad"))
        dry_run = _as_bool_local(request.data.get("dry_run", True))

        # Conteos previos
        cnt_res = abono.turnos_reservados.count()
        cnt_pri = abono.turnos_prioridad.count()

        if dry_run:
            return Response({
                "dry_run": True,
                "solo_prioridad": solo_prioridad,
                "resumen": {
                    "turnos_reservados_afectados": 0 if solo_prioridad else cnt_res,
                    "turnos_prioridad_afectados": cnt_pri,
                }
            }, status=200)

        # --- LIBERACIÓN ---
        afectados_res = 0
        afectados_pri = 0

        # 1) Prioridades → limpiar vínculo y desbloquear como clase suelta
        pri_qs = abono.turnos_prioridad.select_for_update()
        afectados_pri = pri_qs.update(abono_mes_prioridad=None, reservado_para_abono=False)
        abono.turnos_prioridad.clear()

        if not solo_prioridad:
            # 2) Reservados → liberar slot y limpiar vínculo
            res_qs = abono.turnos_reservados.select_for_update()
            # No emitimos bonificaciones acá: es una operación administrativa de “liberar”
            for t in res_qs:
                t.usuario = None
                t.estado = "disponible"
                t.abono_mes_reservado = None
                # Extras solicitados: devolver campos a su estado normal
                update_fields = ["usuario", "estado", "abono_mes_reservado"]
                if hasattr(t, "reservado_para_abono"):
                    t.reservado_para_abono = False
                    update_fields.append("reservado_para_abono")
                if hasattr(t, "comprobante_abono_id"):
                    t.comprobante_abono = None
                    update_fields.append("comprobante_abono")
                t.save(update_fields=update_fields)
                afectados_res += 1

            abono.turnos_reservados.clear()

            # 3) Marcar abono cancelado
            abono.estado = "cancelado"
            abono.save(update_fields=["estado"])


    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /padel/abonos/{id}/
        Elimina un AbonoMes liberando antes TODOS sus vínculos:
        - Turnos reservados: usuario=NULL, estado="disponible", abono_mes_reservado=NULL, reservado_para_abono=False, comprobante_abono=NULL
        - Turnos prioridad: abono_mes_prioridad=NULL, reservado_para_abono=False
        - Limpia las M2M y borra el AbonoMes.
        Respeta alcance para admin_cliente.
        """
        abono = self.get_object()

        # Tenancy para admin_cliente
        user = request.user
        if not user.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            
            if rol_actual == "admin_cliente":
                cliente_actual = getattr(request, 'cliente_actual', None)
                if not cliente_actual or getattr(abono.sede, "cliente_id", None) != cliente_actual.id:
                    return Response({"detail": "No autorizado para este abono."}, status=403)

        # 1) Prioridades
        pri_qs = abono.turnos_prioridad.select_for_update()
        pri_qs.update(abono_mes_prioridad=None, reservado_para_abono=False)
        abono.turnos_prioridad.clear()

        # 2) Reservados
        afectados_res = 0
        res_qs = abono.turnos_reservados.select_for_update()
        for t in res_qs:
            t.usuario = None
            t.estado = "disponible"
            t.abono_mes_reservado = None
            update_fields = ["usuario", "estado", "abono_mes_reservado"]
            if hasattr(t, "reservado_para_abono"):
                t.reservado_para_abono = False
                update_fields.append("reservado_para_abono")
            if hasattr(t, "comprobante_abono_id"):
                t.comprobante_abono = None
                update_fields.append("comprobante_abono")
            t.save(update_fields=update_fields)
            afectados_res += 1
        abono.turnos_reservados.clear()

        # 3) Borrar el abono
        abono_id = abono.id
        super().destroy(request, *args, **kwargs)

        return Response({
            "ok": True,
            "abono_eliminado": abono_id,
            "resumen": {
                "turnos_reservados_afectados": afectados_res,
                "turnos_prioridad_afectados": pri_qs.count(),  # nota: count() acá ya no refleja el update; es informativo
            }
        }, status=200)

        return Response({
            "ok": True,
            "solo_prioridad": solo_prioridad,
            "resumen": {
                "turnos_reservados_afectados": afectados_res,
                "turnos_prioridad_afectados": afectados_pri,
                "abono_estado": abono.estado,
            }
        }, status=200)


class TipoAbonoPadelViewSet(viewsets.ModelViewSet):
    """
    CRUD de tipos de abono por sede.
    - Restringe por cliente salvo super_admin.
    - Filtra por sede_id (query param).
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin | SoloLecturaUsuariosFinalesYEmpleados]
    serializer_class = TipoAbonoPadelSerializer

    def get_queryset(self):
        user = self.request.user
        sede_id = self.request.query_params.get("sede_id")
        qs = TipoAbonoPadel.objects.select_related("configuracion_sede__sede")

        if not user.is_super_admin:
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(self.request)
            
            if rol_actual != "super_admin":
                cliente_actual = getattr(self.request, 'cliente_actual', None)
                if cliente_actual:
                    qs = qs.filter(configuracion_sede__sede__cliente=cliente_actual)

        if sede_id:
            qs = qs.filter(configuracion_sede__sede_id=sede_id)

        return qs


def _as_bool(val) -> bool:
    # 🔁 Helper fuera de clase para compatibilidad retro (considerar desuso si no se usa externamente).
    if val is True:
        return True
    if val is False or val is None:
        return False
    return str(val).strip().lower() in ("1", "true", "t", "yes", "y", "on")
