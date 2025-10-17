# apps/pagos_core/views.py

from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination

from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import PermissionDenied
import logging
import os

from apps.pagos_core.services.comprobantes import ComprobanteService
from apps.pagos_core.models import ComprobantePago, ComprobanteAbono, PagoIntento
from apps.pagos_core.serializers import (
    ComprobantePagoSerializer,
    ComprobanteUploadSerializer,
    ComprobanteAbonoSerializer,
    ComprobanteAbonoUploadSerializer,
)
from apps.pagos_core.filters import ComprobantePagoFilter

from apps.common.permissions import EsAdminDeSuCliente, EsSuperAdmin

from django.db import transaction

from apps.turnos_padel.models import AbonoMes
from apps.turnos_core.models import Turno, TurnoBonificado
from apps.turnos_padel.services.abonos import confirmar_y_reservar_abono

from decimal import Decimal, InvalidOperation
from apps.turnos_padel.serializers import AbonoMesSerializer
from apps.turnos_core.services.bonificaciones import bonificaciones_vigentes

from django.db.models import Exists, OuterRef
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


class ComprobanteView(ListCreateAPIView):
    pagination_class = PageNumberPagination
    """
    🔹 Listado y carga de comprobantes de pago de turnos individuales.

    - GET: listado con filtros por cliente/usuario (scope por rol).
    - POST: subida de comprobante (archivo obligatorio, OCR + validaciones).
    - Query param: `solo_preaprobados=1` → filtra por PagoIntento en estado "pre_aprobado".
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ComprobanteUploadSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ComprobantePagoFilter
    ordering_fields = ["created_at", "valido"]
    ordering = ["-created_at"]
    
    def get_serializer_class(self):
        return ComprobanteUploadSerializer if self.request.method == "POST" else ComprobantePagoSerializer

    def get_queryset(self):
        usuario = self.request.user
        
        # 🔎 Extra: filtros por estado de pago
        solo_preaprobados = self.request.query_params.get("solo_preaprobados", "").lower() in ("1", "true", "t", "yes")
        solo_aprobados = self.request.query_params.get("solo_aprobados", "").lower() in ("1", "true", "t", "yes")
        solo_rechazados = self.request.query_params.get("solo_rechazados", "").lower() in ("1", "true", "t", "yes")
        
        # 🔎 Filtros por usuario específico
        usuario_id = self.request.query_params.get("usuario_id")
        usuario_email = self.request.query_params.get("usuario_email")
        
        # Aplicar filtros por usuario si se especifican
        filtros_usuario = {}
        if usuario_id:
            filtros_usuario["turno__usuario__id"] = usuario_id
        if usuario_email:
            filtros_usuario["turno__usuario__email__icontains"] = usuario_email
        
        if solo_preaprobados:
            # Solo ComprobantePago con PagoIntento pre_aprobado Y sin otros estados
            ct_pago = ContentType.objects.get_for_model(ComprobantePago)
            intentos_pre_pago = PagoIntento.objects.filter(
                content_type=ct_pago,
                object_id=OuterRef("pk"),
                estado="pre_aprobado",
            )
            intentos_otros_estados = PagoIntento.objects.filter(
                content_type=ct_pago,
                object_id=OuterRef("pk"),
                estado__in=["confirmado", "rechazado"],
            )
            
            qs = (
                ComprobantePago.objects
                .select_related("turno", "turno__usuario", "turno__lugar", "cliente")
                .annotate(
                    tiene_preaprobado=Exists(intentos_pre_pago),
                    tiene_otros_estados=Exists(intentos_otros_estados)
                )
                .filter(tiene_preaprobado=True, tiene_otros_estados=False, **filtros_usuario)
                .order_by("-created_at")
            )
        elif solo_aprobados:
            # Solo ComprobantePago con PagoIntento confirmado
            ct_pago = ContentType.objects.get_for_model(ComprobantePago)
            intentos_confirmados = PagoIntento.objects.filter(
                content_type=ct_pago,
                object_id=OuterRef("pk"),
                estado="confirmado",
            )
            
            qs = (
                ComprobantePago.objects
                .select_related("turno", "turno__usuario", "turno__lugar", "cliente")
                .annotate(tiene_confirmado=Exists(intentos_confirmados))
                .filter(tiene_confirmado=True, **filtros_usuario)
                .order_by("-created_at")
            )
        elif solo_rechazados:
            # Solo ComprobantePago con PagoIntento rechazado
            ct_pago = ContentType.objects.get_for_model(ComprobantePago)
            intentos_rechazados = PagoIntento.objects.filter(
                content_type=ct_pago,
                object_id=OuterRef("pk"),
                estado="rechazado",
            )
            
            qs = (
                ComprobantePago.objects
                .select_related("turno", "turno__usuario", "turno__lugar", "cliente")
                .annotate(tiene_rechazado=Exists(intentos_rechazados))
                .filter(tiene_rechazado=True, **filtros_usuario)
                .order_by("-created_at")
            )
        else:
            # Comportamiento normal: todos los ComprobantePago
            qs = (
                ComprobantePago.objects
                .select_related("turno", "turno__usuario", "turno__lugar", "cliente")
                .filter(**filtros_usuario)
                .order_by("-created_at")
            )

        # 🔐 Scope por tipo de usuario
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Super admin (usar nuevo campo)
        if usuario.is_super_admin:
            pass
        # Admin del cliente → comprobantes de su cliente
        elif cliente_actual:
            qs = qs.filter(cliente=cliente_actual)
        # Empleado/usuario final → solo sus propios comprobantes
        else:
            qs = qs.filter(turno__usuario=usuario)
        
        return qs

    def post(self, request, *args, **kwargs):
        """
        ➜ Subida de comprobante de pago.
        - Valida con `ComprobanteUploadSerializer` (OCR + reglas de negocio).
        - Devuelve mensaje de éxito + datos extraídos.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comprobante = serializer.save()
        return Response({
            "mensaje": "✅ Comprobante recibido y validado correctamente",
            "datos_extraidos": comprobante.datos_extraidos,
            "turno_id": comprobante.turno.id,
            "id_comprobante": comprobante.id
        }, status=status.HTTP_201_CREATED)


class ComprobanteDownloadView(APIView):
    """
    🔹 Descarga segura de archivos de comprobantes.
    - Valida permisos con ComprobanteService.
    - Devuelve FileResponse binario.
    """
    queryset = ComprobantePago.objects.none()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        logger.debug("Descarga de comprobante %s solicitada por %s (%s)", pk, request.user, getattr(request.user, "tipo_usuario", ""))

        try:
            comprobante = ComprobanteService.download_comprobante(comprobante_id=int(pk), usuario=request.user)
            if not comprobante.archivo or not comprobante.archivo.storage.exists(comprobante.archivo.name):
                logger.error("Archivo no encontrado en storage: %s", comprobante.archivo.name)
                return Response({"error": "Archivo no encontrado en disco"}, status=404)

            return FileResponse(
                comprobante.archivo.open("rb"),
                as_attachment=True,
                filename=comprobante.archivo.name.split("/")[-1]
            )
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)


class ComprobanteAbonoDownloadView(APIView):
    """
    🔹 Descarga segura de archivos de comprobantes de abono.
    - Valida permisos con ComprobanteService.
    - Devuelve FileResponse binario.
    """
    queryset = ComprobanteAbono.objects.none()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        logger.debug("Descarga de comprobante abono %s solicitada por %s (%s)", pk, request.user, getattr(request.user, "tipo_usuario", ""))

        try:
            # Buscar directamente en ComprobanteAbono, no usar el método genérico
            comprobante = ComprobanteAbono.objects.get(pk=int(pk))
            if not comprobante.archivo:
                raise PermissionDenied("El comprobante no tiene archivo asociado.")

            # Validar permisos
            from apps.auth_core.utils import get_rol_actual_del_jwt
            rol_actual = get_rol_actual_del_jwt(request)
            cliente_actual = getattr(request, 'cliente_actual', None)
            
            if request.user.is_authenticated and request.user.is_super_admin:
                pass  # Super admin puede ver todo
            elif request.user.is_authenticated and rol_actual == "admin_cliente":
                if comprobante.cliente != cliente_actual:
                    raise PermissionDenied("No tenés permiso para ver este comprobante.")
            elif comprobante.abono_mes and comprobante.abono_mes.usuario != request.user:
                raise PermissionDenied("No tenés permiso para ver este comprobante.")
            else:
                raise PermissionDenied("No tenés permiso para ver este comprobante.")

            if not comprobante.archivo.storage.exists(comprobante.archivo.name):
                logger.error("Archivo no encontrado en storage: %s", comprobante.archivo.name)
                return Response({"error": "Archivo no encontrado en disco"}, status=404)

            return FileResponse(
                comprobante.archivo.open("rb"),
                as_attachment=True,
                filename=comprobante.archivo.name.split("/")[-1]
            )
        except ComprobanteAbono.DoesNotExist:
            return Response({"error": "Comprobante de abono no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.exception("Error descargando comprobante abono %s", pk)
            return Response({"error": "Error interno"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ComprobanteAprobarRechazarView(APIView):
    """
    🔹 Aprobación o rechazo de comprobantes (admin/super).

    - PATCH /comprobantes/{id}/aprobar/
    - PATCH /comprobantes/{id}/rechazar/
    - Aplica tanto a `ComprobantePago` (turnos individuales) como a `ComprobanteAbono` (abonos mensuales).
    - Actualiza estados en PagoIntento, Turno/AbonoMes según corresponda.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin]

    @transaction.atomic
    def patch(self, request, pk, action):
        logger.debug("[PATCH] Acción '%s' sobre comprobante ID=%s", action, pk)

        # 1) Comprobante de turno individual
        try:
            comprobante = ComprobantePago.objects.get(pk=pk)
            logger.debug("[PATCH] ComprobantePago encontrado: %s", comprobante.id)
            
            if action == "aprobar":
                # Aprobar comprobante
                comprobante.valido = True
                comprobante.save(update_fields=["valido"])
                
                # Actualizar PagoIntento
                ct_pago = ContentType.objects.get_for_model(ComprobantePago)
                pago_intento = PagoIntento.objects.filter(
                    content_type=ct_pago,
                    object_id=comprobante.id,
                    estado="pre_aprobado"
                ).first()
                
                if pago_intento:
                    pago_intento.estado = "confirmado"
                    pago_intento.save(update_fields=["estado"])
                
                # Actualizar estado del turno
                if comprobante.turno:
                    comprobante.turno.estado = "confirmado"
                    comprobante.turno.save(update_fields=["estado"])
                
                logger.info("[PATCH] ComprobantePago %s aprobado exitosamente", comprobante.id)
                return Response({"message": "Comprobante aprobado exitosamente"}, status=200)
                
            elif action == "rechazar":
                # Rechazar comprobante
                comprobante.valido = False
                comprobante.save(update_fields=["valido"])
                
                # Actualizar PagoIntento
                ct_pago = ContentType.objects.get_for_model(ComprobantePago)
                pago_intento = PagoIntento.objects.filter(
                    content_type=ct_pago,
                    object_id=comprobante.id,
                    estado="pre_aprobado"
                ).first()
                
                if pago_intento:
                    pago_intento.estado = "rechazado"
                    pago_intento.save(update_fields=["estado"])
                
                # Liberar turno
                if comprobante.turno:
                    comprobante.turno.estado = "disponible"
                    comprobante.turno.usuario = None
                    comprobante.turno.save(update_fields=["estado", "usuario"])
                
                logger.info("[PATCH] ComprobantePago %s rechazado exitosamente", comprobante.id)
                return Response({"message": "Comprobante rechazado exitosamente"}, status=200)
                
        except ComprobantePago.DoesNotExist:
            logger.debug("[PATCH] No es ComprobantePago. Probando ComprobanteAbono...")

        # 2) Comprobante de abono mensual
        try:
            comprobante_abono = ComprobanteAbono.objects.select_related("abono_mes").get(pk=pk)
            logger.debug("[PATCH] ComprobanteAbono encontrado: %s", comprobante_abono.id)
            
            if action == "aprobar":
                # Aprobar abono
                comprobante_abono.valido = True
                comprobante_abono.save(update_fields=["valido"])
                
                # Actualizar PagoIntento
                ct_abono = ContentType.objects.get_for_model(ComprobanteAbono)
                pago_intento = PagoIntento.objects.filter(
                    content_type=ct_abono,
                    object_id=comprobante_abono.id,
                    estado="pre_aprobado"
                ).first()
                
                if pago_intento:
                    pago_intento.estado = "confirmado"
                    pago_intento.save(update_fields=["estado"])
                
                # Actualizar estado del abono
                abono = comprobante_abono.abono_mes
                abono.estado = "pagado"
                abono.save(update_fields=["estado"])
                
                logger.info("[PATCH] Abono %s aprobado exitosamente", abono.id)
                return Response({"message": "Abono aprobado exitosamente"}, status=200)
                
            elif action == "rechazar":
                # Rechazar abono
                comprobante_abono.valido = False
                comprobante_abono.save(update_fields=["valido"])
                
                # Actualizar PagoIntento
                ct_abono = ContentType.objects.get_for_model(ComprobanteAbono)
                pago_intento = PagoIntento.objects.filter(
                    content_type=ct_abono,
                    object_id=comprobante_abono.id,
                    estado="pre_aprobado"
                ).first()
                
                if pago_intento:
                    pago_intento.estado = "rechazado"
                    pago_intento.save(update_fields=["estado"])
                
                # Liberar turnos reservados
                abono = comprobante_abono.abono_mes
                for turno in abono.turnos_reservados.all():
                    turno.estado = "disponible"
                    turno.usuario = None
                    turno.save(update_fields=["estado", "usuario"])
                
                # Cambiar estado del abono
                abono.estado = "cancelado"
                abono.save(update_fields=["estado"])
                
                logger.info("[PATCH] Abono %s rechazado exitosamente", abono.id)
                return Response({"message": "Abono rechazado exitosamente"}, status=200)
            
        except ComprobanteAbono.DoesNotExist:
            return Response({"error": "No encontrado"}, status=404)


class ComprobanteAprobarLoteView(APIView):
    """
    🔹 Aprobación en lote de comprobantes (admin/super).
    
    - POST /comprobantes/aprobar-lote/
    - Acepta una lista de IDs de comprobantes para aprobar
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin]

    @transaction.atomic
    def post(self, request):
        comprobante_ids = request.data.get('comprobante_ids', [])
        if not comprobante_ids:
            return Response({"error": "No se proporcionaron IDs de comprobantes"}, status=400)
        
        aprobados = []
        errores = []
        
        for comprobante_id in comprobante_ids:
            try:
                # Intentar con ComprobantePago
                try:
                    comprobante = ComprobantePago.objects.get(pk=comprobante_id)
                    self._aprobar_comprobante_pago(comprobante)
                    aprobados.append(f"ComprobantePago {comprobante_id}")
                except ComprobantePago.DoesNotExist:
                    # Intentar con ComprobanteAbono
                    try:
                        comprobante_abono = ComprobanteAbono.objects.get(pk=comprobante_id)
                        self._aprobar_comprobante_abono(comprobante_abono)
                        aprobados.append(f"ComprobanteAbono {comprobante_id}")
                    except ComprobanteAbono.DoesNotExist:
                        errores.append(f"Comprobante {comprobante_id} no encontrado")
            except Exception as e:
                errores.append(f"Error en comprobante {comprobante_id}: {str(e)}")
        
        return Response({
            "aprobados": aprobados,
            "errores": errores,
            "total_aprobados": len(aprobados),
            "total_errores": len(errores)
        }, status=200)
    
    def _aprobar_comprobante_pago(self, comprobante):
        """Aprobar un ComprobantePago"""
        comprobante.valido = True
        comprobante.save(update_fields=["valido"])
        
        # Actualizar PagoIntento
        ct_pago = ContentType.objects.get_for_model(ComprobantePago)
        pago_intento = PagoIntento.objects.filter(
            content_type=ct_pago,
            object_id=comprobante.id,
            estado="pre_aprobado"
        ).first()
        
        if pago_intento:
            pago_intento.estado = "confirmado"
            pago_intento.save(update_fields=["estado"])
        
        # Actualizar estado del turno
        if comprobante.turno:
            comprobante.turno.estado = "confirmado"
            comprobante.turno.save(update_fields=["estado"])
    
    def _aprobar_comprobante_abono(self, comprobante_abono):
        """Aprobar un ComprobanteAbono"""
        comprobante_abono.valido = True
        comprobante_abono.save(update_fields=["valido"])
        
        # Actualizar PagoIntento
        ct_abono = ContentType.objects.get_for_model(ComprobanteAbono)
        pago_intento = PagoIntento.objects.filter(
            content_type=ct_abono,
            object_id=comprobante_abono.id,
            estado="pre_aprobado"
        ).first()
        
        if pago_intento:
            pago_intento.estado = "confirmado"
            pago_intento.save(update_fields=["estado"])
        
        # Actualizar estado del abono
        abono = comprobante_abono.abono_mes
        abono.estado = "pagado"
        abono.save(update_fields=["estado"])

    def _borrar_archivo_comprobante(self, comprobante):
        """
        Borra el archivo del comprobante del sistema de archivos cuando el pago se confirma.
        Mantiene el registro en BD para auditoría pero elimina el archivo físico.
        """
        try:
            if comprobante.archivo and comprobante.archivo.storage.exists(comprobante.archivo.name):
                # Obtener información del archivo antes de borrarlo
                archivo_path = comprobante.archivo.path
                archivo_size = 0
                if os.path.exists(archivo_path):
                    archivo_size = os.path.getsize(archivo_path)
                
                # Borrar archivo del sistema de archivos
                comprobante.archivo.delete(save=False)
                
                logger.info(
                    f"[PAGO_CONFIRMADO] Archivo borrado: {comprobante.archivo.name} "
                    f"(tamaño: {archivo_size} bytes, comprobante_id: {comprobante.id})"
                )
            else:
                logger.warning(
                    f"[PAGO_CONFIRMADO] Archivo no encontrado para comprobante {comprobante.id}"
                )
        except Exception as e:
            logger.error(
                f"[PAGO_CONFIRMADO] Error borrando archivo del comprobante {comprobante.id}: {str(e)}"
            )


class PagosPendientesCountView(APIView):
    """
    🔹 Métrica rápida: cantidad de comprobantes pendientes de validación para el cliente.
    - Solo accesible por admin_cliente/super_admin.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [EsAdminDeSuCliente | EsSuperAdmin]

    def get(self, request):
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        # Super admin → todos los comprobantes pendientes
        if request.user.is_super_admin:
            count = ComprobantePago.objects.filter(valido=False).count()
        # Admin del cliente → comprobantes pendientes de su cliente
        elif cliente_actual:
            count = ComprobantePago.objects.filter(cliente=cliente_actual, valido=False).count()
        else:
            count = 0
            
        return Response({"count": count})


class ComprobanteAbonoView(APIView):
    """
    🔹 Confirmación de abono mensual (usuario final).
    - POST con `abono_mes_id`, bonificaciones y comprobante (si neto > 0).
    - Aplica bonos automáticamente a turnos reservados.
    - Estado final: `pagado` si neto=0; `pendiente_validacion` si requiere comprobante.
    - Limpia abono vacío si falla la validación.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _cleanup_abono_si_corresponde(self, user, abono_id, reason=""):
        """
        🔧 Elimina el AbonoMes si no tiene turnos asignados y ocurrió un fallo en confirmación.
        Evita basura en la BD.
        """
        try:
            with transaction.atomic():
                abono = AbonoMes.objects.filter(id=abono_id, usuario=user).first()
                if abono and abono.turnos_reservados.count() == 0 and abono.turnos_prioridad.count() == 0:
                    logger.info("[abono.cleanup] Eliminando abono %s (motivo: %s)", abono_id, reason)
                    abono.delete()
        except Exception as e:
            logger.warning("[abono.cleanup] No se pudo eliminar abono %s: %s", abono_id, str(e))

    def post(self, request, *args, **kwargs):
        """
        ➜ Flujo de confirmación:
        - Verifica abono y precios.
        - Calcula neto = precio_abono - (bonos * precio_clase).
        - Aplica bonificaciones en orden cronológico.
        - Exige comprobante si neto > 0.
        - Retorna estado del abono + resumen (bonos aplicados, neto, etc).
        """
        abono_id = request.data.get("abono_mes_id")
        if not abono_id:
            raise serializers.ValidationError({"abono_mes_id": "Este campo es obligatorio."})

        # ... lógica de cálculo, aplicación de bonos y confirmación ...


class ComprobanteAbonoView(ListCreateAPIView):
    pagination_class = PageNumberPagination
    """
    🔹 Listado y carga de comprobantes de abonos mensuales.

    - GET: listado con filtros por cliente/usuario (scope por rol).
    - POST: subida de comprobante (archivo obligatorio, OCR + validaciones).
    - Query param: `solo_preaprobados=1` → filtra por PagoIntento en estado "pre_aprobado".
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ComprobanteAbonoUploadSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at", "valido"]
    ordering = ["-created_at"]
    
    def get_serializer_class(self):
        return ComprobanteAbonoUploadSerializer if self.request.method == "POST" else ComprobanteAbonoSerializer

    def get_queryset(self):
        usuario = self.request.user
        
        # 🔎 Extra: filtros por estado de pago
        solo_preaprobados = self.request.query_params.get("solo_preaprobados", "").lower() in ("1", "true", "t", "yes")
        solo_aprobados = self.request.query_params.get("solo_aprobados", "").lower() in ("1", "true", "t", "yes")
        solo_rechazados = self.request.query_params.get("solo_rechazados", "").lower() in ("1", "true", "t", "yes")
        
        if solo_preaprobados:
            # Solo ComprobanteAbono con PagoIntento pre_aprobado Y sin otros estados
            ct_abono = ContentType.objects.get_for_model(ComprobanteAbono)
            intentos_pre_abono = PagoIntento.objects.filter(
                content_type=ct_abono,
                object_id=OuterRef("pk"),
                estado="pre_aprobado",
            )
            intentos_otros_estados = PagoIntento.objects.filter(
                content_type=ct_abono,
                object_id=OuterRef("pk"),
                estado__in=["confirmado", "rechazado"],
            )
            
            qs = (
                ComprobanteAbono.objects
                .select_related("abono_mes", "abono_mes__usuario", "cliente")
                .annotate(
                    tiene_preaprobado=Exists(intentos_pre_abono),
                    tiene_otros_estados=Exists(intentos_otros_estados)
                )
                .filter(tiene_preaprobado=True, tiene_otros_estados=False)
                .order_by("-created_at")
            )
        elif solo_aprobados:
            # Solo ComprobanteAbono con PagoIntento confirmado
            ct_abono = ContentType.objects.get_for_model(ComprobanteAbono)
            intentos_confirmados = PagoIntento.objects.filter(
                content_type=ct_abono,
                object_id=OuterRef("pk"),
                estado="confirmado",
            )
            
            qs = (
                ComprobanteAbono.objects
                .select_related("abono_mes", "abono_mes__usuario", "cliente")
                .annotate(tiene_confirmado=Exists(intentos_confirmados))
                .filter(tiene_confirmado=True)
                .order_by("-created_at")
            )
        elif solo_rechazados:
            # Solo ComprobanteAbono con PagoIntento rechazado
            ct_abono = ContentType.objects.get_for_model(ComprobanteAbono)
            intentos_rechazados = PagoIntento.objects.filter(
                content_type=ct_abono,
                object_id=OuterRef("pk"),
                estado="rechazado",
            )
            
            qs = (
                ComprobanteAbono.objects
                .select_related("abono_mes", "abono_mes__usuario", "cliente")
                .annotate(tiene_rechazado=Exists(intentos_rechazados))
                .filter(tiene_rechazado=True)
                .order_by("-created_at")
            )
        else:
            # Comportamiento normal: todos los ComprobanteAbono
            qs = (
                ComprobanteAbono.objects
                .select_related("abono_mes", "abono_mes__usuario", "cliente")
                .order_by("-created_at")
            )

        # 🔐 Scope por tipo de usuario
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Super admin (usar nuevo campo)
        if usuario.is_super_admin:
            pass
        # Admin del cliente → comprobantes de abono de su cliente
        elif cliente_actual:
            qs = qs.filter(cliente=cliente_actual)
        # Empleado/usuario final → solo sus propios comprobantes de abono
        else:
            qs = qs.filter(abono_mes__usuario=usuario)
        
        return qs

    def post(self, request, *args, **kwargs):
        """
        ➜ Subida de comprobante de abono.
        - Valida con `ComprobanteAbonoUploadSerializer` (OCR + reglas de negocio).
        """
        return super().post(request, *args, **kwargs)
