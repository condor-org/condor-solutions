# apps/turnos_padel_core/views.py
from rest_framework.decorators import action
from rest_framework import status, viewsets, permissions
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from .models import Profesor, Disponibilidad
from apps.turnos_core.models import BloqueoTurnos, Turno, Lugar
from apps.turnos_core.serializers import BloqueoTurnosSerializer
from .serializers import ProfesorSerializer, DisponibilidadSerializer, TurnoSerializer
from rest_framework.views import APIView
from .services.generador import generar_turnos_del_mes
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
import logging
logger = logging.getLogger(__name__)


class ProfesorViewSet(viewsets.ModelViewSet):
    queryset = Profesor.objects.all()
    serializer_class = ProfesorSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


    @action(detail=True, methods=["get"], url_path="turnos",permission_classes=[IsAuthenticated])
    def turnos(self, request, pk=None):
        """
        GET /padel/profesores/{pk}/turnos/
        Devuelve los turnos de este profesor con fecha >= hoy.
        Parámetro opcional: ?lugar_id=3 para filtrar por sede.
        """
        profesor = self.get_object()
        ct = ContentType.objects.get_for_model(Profesor)

        # Fecha mínima = hoy
        hoy = timezone.localdate()

        # Base queryset
        qs = Turno.objects.filter(
            content_type=ct,
            object_id=profesor.id,
            fecha__gte=hoy
        )

        # Filtrado por sede si viene
        lugar_id = request.query_params.get("lugar_id")
        if lugar_id is not None:
            qs = qs.filter(lugar_id=lugar_id)

        serializer = TurnoSerializer(qs.order_by("fecha", "hora"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        profesor = self.get_object()
        serializer = self.get_serializer(profesor)
        # Traer bloqueos activos de este profesor
        ct = ContentType.objects.get_for_model(Profesor)
        bloqueos = BloqueoTurnos.objects.filter(
            content_type=ct,
            object_id=profesor.id,
            activo=True
        )
        bloqueos_serializer = BloqueoTurnosSerializer(bloqueos, many=True)
        data = serializer.data
        data['bloqueos'] = bloqueos_serializer.data
        return Response(data)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsAdminUser])
    def disponibilidades(self, request, pk=None):
        profesor = self.get_object()
        disponibilidades = profesor.disponibilidades.filter(activo=True)
        serializer = DisponibilidadSerializer(disponibilidades, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post", "put", "delete"], permission_classes=[IsAuthenticated, IsAdminUser])
    def bloqueos(self, request, pk=None):
        profesor = self.get_object()
        ct = ContentType.objects.get_for_model(Profesor)

        if request.method == "GET":
            bloqueos = BloqueoTurnos.objects.filter(content_type=ct, object_id=profesor.id, activo=True)
            serializer = BloqueoTurnosSerializer(bloqueos, many=True)
            return Response(serializer.data)

        if request.method == "POST":
            data = request.data.copy()
            data["content_type"] = ct.pk
            data["object_id"] = profesor.id
            serializer = BloqueoTurnosSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            bloqueo = serializer.save()

            # Opcional: eliminar turnos afectados por bloqueo
            reporte = self.eliminar_turnos_bloqueados(bloqueo)
            response_data = {
                **serializer.data,
                "turnos_reservados_afectados": reporte
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        if request.method == "PUT":
            bloqueo_id = request.data.get("id")
            bloqueo = get_object_or_404(BloqueoTurnos, id=bloqueo_id, content_type=ct, object_id=profesor.id)
            serializer = BloqueoTurnosSerializer(bloqueo, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            bloqueo = serializer.save()

            # Opcional: actualizar turnos bloqueados
            self.eliminar_turnos_bloqueados(bloqueo)

            return Response(serializer.data)

        if request.method == "DELETE":
            bloqueo_id = request.data.get("id")
            bloqueo = get_object_or_404(BloqueoTurnos, id=bloqueo_id, content_type=ct, object_id=profesor.id)
            
            # 🔥 Restaurar turnos cancelados antes de desactivar el bloqueo
            self.restaurar_turnos_cancelados(bloqueo)

            # Desactivar el bloqueo (no eliminar)
            bloqueo.activo = False
            bloqueo.save()

            return Response(status=status.HTTP_204_NO_CONTENT)

    def eliminar_turnos_bloqueados(self, bloqueo):
        filtros = {
            "content_type": bloqueo.content_type,
            "object_id":    bloqueo.object_id,
            "fecha__gte":   bloqueo.fecha_inicio,
            "fecha__lte":   bloqueo.fecha_fin,
        }
        if bloqueo.lugar is not None:
            filtros["lugar"] = bloqueo.lugar

        logger.debug(f"[Bloqueo {bloqueo.id}] filtros aplicados: {filtros}")

        qs = Turno.objects.filter(**filtros)
        total = qs.count()
        logger.debug(f"[Bloqueo {bloqueo.id}] total turnos en rango: {total}")

        disponibles = qs.filter(estado="disponible")
        cnt_disp = disponibles.count()
        logger.debug(f"[Bloqueo {bloqueo.id}] disponibles a cancelar: {cnt_disp}")
        disponibles.update(estado="cancelado")

        reservados = qs.filter(estado="reservado")
        cnt_res = reservados.count()
        logger.debug(f"[Bloqueo {bloqueo.id}] reservados sin tocar: {cnt_res}")

        reporte = []
        for t in reservados:
            reporte.append({
                "id":    t.id,
                "fecha": t.fecha.strftime("%Y-%m-%d"),
                "hora":  t.hora.strftime("%H:%M"),
                "usuario": str(t.usuario) if t.usuario else "Desconocido",
                "email":   t.usuario.email if t.usuario else "Desconocido",
            })
        logger.debug(f"[Bloqueo {bloqueo.id}] reporte final: {reporte}")

        return reporte

    def restaurar_turnos_cancelados(self, bloqueo):
        """
        1) Auto-cancelados (sin usuario) → disponibles
        2) Forzados (con usuario) → reservados
        """
        # —————— LOGGING DE ARRANQUE ——————
        logger.debug(f"[RESTAURAR-INICIO] bloqueo_id={bloqueo.id} "
                    f"profesor={bloqueo.object_id} "
                    f"lugar={bloqueo.lugar} "
                    f"rango={bloqueo.fecha_inicio}→{bloqueo.fecha_fin}")

        filtros = {
            "content_type": bloqueo.content_type,
            "object_id":    bloqueo.object_id,
            "fecha__gte":   bloqueo.fecha_inicio,
            "fecha__lte":   bloqueo.fecha_fin,
        }
        if bloqueo.lugar is not None:
            filtros["lugar"] = bloqueo.lugar

        # —————— LOGGING DE FILTROS ——————
        logger.debug(f"[RESTAURAR-FILTROS] {filtros}")

        # Consulta de todos los cancelados
        qs_cancelados = Turno.objects.filter(**filtros, estado="cancelado")
        total_cancel = qs_cancelados.count()
        logger.debug(f"[RESTAURAR-TOTALES] total_cancelados={total_cancel}")

        # 1) Auto-cancelados → disponibles
        cnt_auto = qs_cancelados.filter(usuario__isnull=True) \
                                .update(estado="disponible")
        logger.debug(f"[RESTAURAR-AUTO] auto-cancelados_restaurados={cnt_auto}")

        # 2) Forzados → reservados
        cnt_forz = qs_cancelados.filter(usuario__isnull=False) \
                                .update(estado="reservado")
        logger.debug(f"[RESTAURAR-FORZ] forzados_restaurados={cnt_forz}")

        # —————— LOGGING DE FIN ——————
        logger.debug(f"[RESTAURAR-FIN] bloqueo_id={bloqueo.id} completo")


    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminUser])
    def forzar_cancelacion_reservados(self, request, pk=None):
        """
        Fuerza la cancelación de turnos reservados para un bloqueo específico.
        Requiere 'bloqueo_id' en el body.
        """
        bloqueo_id = request.data.get("bloqueo_id")
        if not bloqueo_id:
            return Response({"error": "Se requiere 'bloqueo_id'."}, status=status.HTTP_400_BAD_REQUEST)

        profesor = self.get_object()
        ct = ContentType.objects.get_for_model(Profesor)
        bloqueo = get_object_or_404(
            BloqueoTurnos,
            id=bloqueo_id,
            content_type=ct,
            object_id=profesor.id
        )

        # Mismos filtros condicionales que en eliminar_turnos_bloqueados
        filtros = {
            "content_type": bloqueo.content_type,
            "object_id": bloqueo.object_id,
            "fecha__gte": bloqueo.fecha_inicio,
            "fecha__lte": bloqueo.fecha_fin,
        }
        if bloqueo.lugar is not None:
            filtros["lugar"] = bloqueo.lugar

        qs = Turno.objects.filter(**filtros, estado="reservado")
        afectados = qs.count()
        qs.update(estado="cancelado")

        return Response({
            "detalle": f"{afectados} turnos reservados fueron cancelados forzadamente.",
            "bloqueo_id": bloqueo.id,
        }, status=status.HTTP_200_OK)


class GenerarTurnosView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        anio = request.data.get("anio")
        mes = request.data.get("mes")
        duracion = request.data.get("duracion_minutos", 60)
        profesor_id = request.data.get("profesor_id")

        if not anio or not mes:
            return Response({"detail": "Se requiere 'año' y 'mes'"}, status=status.HTTP_400_BAD_REQUEST)

        profesores = Profesor.objects.all()
        if profesor_id:
            profesores = profesores.filter(id=profesor_id)

        total = 0
        detalle = []

        for profe in profesores:
            previos = generar_turnos_del_mes(anio, mes, duracion, profesor_id=profe.id)
            detalle.append({
                "profesor_id": profe.id,
                "nombre": profe.nombre,
                "turnos": previos
            })
            total += previos

        return Response({
            "turnos_generados": total,
            "profesores_afectados": profesores.count(),
            "detalle": detalle
        })

class ProfesorBloqueoViewSet(viewsets.ModelViewSet):
    serializer_class = BloqueoTurnosSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        profesor_id = self.kwargs['profesor_pk']
        ct = ContentType.objects.get(model='profesor')
        return BloqueoTurnos.objects.filter(content_type=ct, object_id=profesor_id)

    def perform_create(self, serializer):
        profesor_id = self.kwargs['profesor_pk']
        ct = ContentType.objects.get(model='profesor')
        serializer.save(content_type=ct, object_id=profesor_id)

    def perform_update(self, serializer):
        # Al actualizar, asegurate que el content_type y object_id no cambien
        profesor_id = self.kwargs['profesor_pk']
        ct = ContentType.objects.get(model='profesor')
        serializer.save(content_type=ct, object_id=profesor_id)

    def destroy(self, request, *args, **kwargs):
        # (opcional) chequeo extra de seguridad
        instance = self.get_object()
        ct = ContentType.objects.get(model='profesor')
        if instance.content_type != ct:
            raise PermissionDenied("No permitido")
        return super().destroy(request, *args, **kwargs)

# --- Profesores disponibles por sede ---
class ProfesoresDisponiblesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        lugar_id = request.query_params.get("lugar_id")
        if not lugar_id:
            return Response({"error": "Falta lugar_id"}, status=400)
        profesores = Profesor.objects.filter(disponibilidades__lugar_id=lugar_id).distinct()
        data = ProfesorSerializer(profesores, many=True).data
        return Response(data)
