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
from django.db.models import Q

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from rest_framework.request import Request
from rest_framework.parsers import JSONParser
from io import BytesIO
import json
from apps.turnos_padel.services.abonos import confirmar_y_reservar_abono
from apps.turnos_padel.services.abonos import validar_y_confirmar_abono, _notify_abono_admin

import logging

logger = logging.getLogger(__name__)

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
        if user.tipo_usuario == "super_admin":
            return (
                Lugar.objects.all()
                .select_related("configuracion_padel")
                .prefetch_related("configuracion_padel__tipos_clase")
            )
        elif user.tipo_usuario == "admin_cliente":
            return (
                Lugar.objects.filter(cliente=user.cliente)
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
        # 🧾 Asigna cliente desde el usuario autenticado (consistencia multi-tenant).
        return serializer.save(cliente=self.request.user.cliente)

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
        qs = ConfiguracionSedePadel.objects.all()

        if user.tipo_usuario == "admin_cliente":
            qs = qs.filter(sede__cliente=user.cliente)
        elif user.tipo_usuario != "super_admin":
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
        logger.info("[AbonoMesViewSet:get_queryset] Usuario: %s (%s)", user.id, user.tipo_usuario)

        if user.tipo_usuario == "super_admin":
            return AbonoMes.objects.all()
        elif user.tipo_usuario == "admin_cliente":
            return AbonoMes.objects.filter(sede__cliente=user.cliente)
        return AbonoMes.objects.filter(usuario=user)

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
        if user.tipo_usuario == "usuario_final":
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

            if user.tipo_usuario == "admin_cliente":
                if target_user.cliente_id != user.cliente_id or sede.cliente_id != user.cliente_id:
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
        tipo_codigo = request.query_params.get("tipo_codigo") # opcional

        # 🔐 Autorización por cliente/sede (multi-tenant).
        sede = Lugar.objects.select_related("cliente").filter(id=sede_id).first()
        if not sede:
            return Response({"detail": "Sede no encontrada"}, status=404)

        user = request.user
        if user.tipo_usuario == "admin_cliente" and sede.cliente_id != getattr(user, "cliente_id", None):
            return Response({"detail": "No autorizado para esta sede"}, status=403)
        if user.tipo_usuario not in ("super_admin", "admin_cliente"):
            if getattr(user, "cliente_id", None) != sede.cliente_id:
                return Response({"detail": "No autorizado"}, status=403)

        # 1) Catálogo de tipos de clase activos (filtrable por código).
        tipos_qs = TipoClasePadel.objects.filter(
            configuracion_sede__sede_id=sede_id,
            activo=True
        ).only("id", "codigo", "precio")
        if tipo_codigo:
            tipos_qs = tipos_qs.filter(codigo=tipo_codigo)

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
        fechas_actual_todas = fechas_mes(anio, mes, dia_semana)
        fechas_actual = [d for d in fechas_actual_todas if d >= hoy]
        prox_anio, prox_mes = proximo_mes(anio, mes)
        fechas_prox = fechas_mes(prox_anio, prox_mes, dia_semana)

        if not fechas_actual and not fechas_prox:
            logger.info("[abonos.disponibles] sin fechas futuras para el día de semana")
            return Response([], status=200)

        fechas_total = fechas_actual + fechas_prox
        logger.debug(
            "[abonos.disponibles] hoy=%s | fechas_actual=%s | fechas_prox=%s | total=%s",
            hoy, len(fechas_actual), len(fechas_prox), len(fechas_total)
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

        horas_libres.sort()
        result = [{"hora": h, "tipo_clase": tipo} for h in horas_libres for tipo in tipos_map]

        logger.info(
            "[abonos.disponibles] sede=%s prestador=%s dsem=%s anio=%s mes=%s -> horas=%s, tipos=%s",
            sede_id, prestador_id, dia_semana, anio, mes, horas_libres, [t["codigo"] for t in tipos_map]
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
        user = request.user
        data = request.data.copy()

        # ➜ Normaliza/valida usuario objetivo según rol (igual que create()).
        usuario_target = data.get("usuario") or data.get("usuario_id")
        if user.tipo_usuario == "usuario_final":
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

            if user.tipo_usuario == "admin_cliente":
                if target_user.cliente_id != user.cliente_id or sede.cliente_id != user.cliente_id:
                    logger.warning(
                        "[abonos.reservar][cliente_mismatch] admin=%s target_user=%s sede=%s",
                        user.id, target_user.id, sede.id
                    )
                    return Response({"detail": "No autorizado para asignar fuera de tu cliente."}, status=403)

        # Flag administrativo opcional.
        forzar_admin = self._as_bool(data.get("forzar_admin"))

        bonificaciones_ids = data.getlist("bonificaciones_ids") if hasattr(data, "getlist") else data.get("bonificaciones_ids", [])
        archivo = data.get("archivo")

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
            logger.info("[abonos.notif] reservar -> admins=%s", admins.count())
        except Exception:
            logger.exception("[notif][abono_reserva][fail]")

        return Response(payload, status=201)
       
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

        if hasattr(user, "cliente") and user.tipo_usuario != "super_admin":
            qs = qs.filter(configuracion_sede__sede__cliente=user.cliente)

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
