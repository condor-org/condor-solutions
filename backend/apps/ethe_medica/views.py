# apps/ethe_medica/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date, timedelta

from apps.ethe_medica.models import (
    Medico, Paciente, ResultadoTest, Establecimiento, CentroAtencion, JerarquiaCentro,
    ProtocoloSeguimiento, SeguimientoPaciente
)
from apps.ethe_medica.serializers import (
    MedicoSerializer, PacienteSerializer, IngresarPacienteSerializer,
    ResultadoTestSerializer, EstablecimientoSerializer, CentroAtencionSerializer,
    JerarquiaCentroSerializer, ProtocoloSeguimientoSerializer, SeguimientoPacienteSerializer,
    ReservarTurnoSerializer, EstadisticasSerializer
)
from apps.ethe_medica.permissions import (
    EsMedicoC1, EsMedicoC2, EsMedicoC3, EsMedicoCualquiera,
    EsPaciente, EsAdminEstablecimiento, EsAdminMinistroSalud,
    PuedeVerPacientes, PuedeCrearPacientes, PuedeRegistrarTests,
    PuedeGestionarCentros, PuedeGestionarMedicos, PuedeVerEstadisticas,
    PuedeGestionarAsignaciones, PuedeGestionarProtocolos
)
from apps.ethe_medica.services.flujo_pacientes import obtener_centros_disponibles_para_paciente
from apps.ethe_medica.services.asignacion_turnos import obtener_turnos_disponibles_para_paciente
from apps.ethe_medica.services.protocolos import (
    programar_seguimientos_paciente, obtener_estadisticas_seguimiento
)


class MedicoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de médicos"""
    serializer_class = MedicoSerializer
    permission_classes = [PuedeGestionarMedicos]
    
    def get_queryset(self):
        """Filtrar médicos por cliente"""
        user = self.request.user
        if user.is_super_admin:
            return Medico.objects.all()
        
        return Medico.objects.filter(user__cliente=user.cliente)
    
    @action(detail=True, methods=['get'])
    def disponibilidades(self, request, pk=None):
        """Obtener disponibilidades de un médico"""
        medico = self.get_object()
        disponibilidades = medico.prestador.disponibilidades.filter(activo=True)
        serializer = self.get_serializer(disponibilidades, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """Obtener estadísticas de un médico"""
        medico = self.get_object()
        
        # Fecha mes actual
        mes_actual = timezone.now().date().replace(day=1)
        
        # Pacientes ingresados (solo para C1)
        pacientes_ingresados = Paciente.objects.filter(medico_ingreso=medico).count()
        
        # Tests realizados
        tests = ResultadoTest.objects.filter(medico=medico)
        tests_mes = tests.filter(fecha_realizacion__gte=mes_actual)
        
        # Por tipo de test
        pocus_count = tests.filter(tipo_test='POCUS').count()
        fibroscan_count = tests.filter(tipo_test='FIBROSCAN').count()
        fib4_count = tests.filter(tipo_test='FIB4').count()
        
        # Derivaciones realizadas
        from apps.ethe_medica.models import HistorialCategoria
        derivaciones = HistorialCategoria.objects.filter(medico=medico)
        derivaciones_mes = derivaciones.filter(fecha_cambio__gte=mes_actual).count()
        
        # Consultas (seguimientos realizados)
        consultas = SeguimientoPaciente.objects.filter(estado='REALIZADO').count()
        
        return Response({
            "pacientes_ingresados": pacientes_ingresados,
            "tests_realizados": tests.count(),
            "tests_realizados_mes": tests_mes.count(),
            "pocus_realizados": pocus_count,
            "fibroscan_realizados": fibroscan_count,
            "fib4_realizados": fib4_count,
            "derivaciones_realizadas": derivaciones.count(),
            "derivaciones_mes": derivaciones_mes,
            "consultas_realizadas": consultas
        })


class PacienteViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de pacientes"""
    serializer_class = PacienteSerializer
    permission_classes = [PuedeVerPacientes]
    filterset_fields = ['categoria_actual', 'activo']
    search_fields = ['documento', 'user__nombre', 'user__apellido']
    
    def get_queryset(self):
        """Filtrar pacientes según rol del usuario"""
        user = self.request.user
        
        if user.is_super_admin:
            return Paciente.objects.all()
        
        # Pacientes solo ven sus propios datos
        if hasattr(user, "paciente_ethe"):
            return Paciente.objects.filter(user=user)
        
        # Médicos y admins ven pacientes de su cliente
        return Paciente.objects.filter(user__cliente=user.cliente)
    
    @action(detail=False, methods=['post'], permission_classes=[PuedeCrearPacientes])
    def ingresar(self, request):
        """Ingresar paciente desde centro C1"""
        serializer = IngresarPacienteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        resultado = serializer.save()
        
        return Response({
            "message": "Paciente ingresado exitosamente",
            "paciente": PacienteSerializer(resultado["paciente"]).data,
            "categoria": resultado["categoria"],
            "centros_disponibles": [
                {"id": c.id, "nombre": c.nombre} 
                for c in resultado["centros_disponibles"]
            ]
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def historial_tests(self, request, pk=None):
        """Obtener historial de tests de un paciente"""
        paciente = self.get_object()
        tests = paciente.resultados_tests.all()
        serializer = ResultadoTestSerializer(tests, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def turnos(self, request, pk=None):
        """Obtener turnos de un paciente"""
        paciente = self.get_object()
        turnos = paciente.user.turnos.all()
        # TODO: Implementar serializer para turnos
        return Response({"turnos": []})
    
    @action(detail=True, methods=['get'])
    def centros_disponibles(self, request, pk=None):
        """Obtener centros disponibles para derivación"""
        paciente = self.get_object()
        
        if paciente.categoria_actual == "C1":
            categoria_destino = "C2"
        elif paciente.categoria_actual == "C2":
            categoria_destino = "C3"
        else:
            return Response({"centros": []})
        
        centros = obtener_centros_disponibles_para_paciente(paciente, categoria_destino)
        return Response({
            "centros": [
                {"id": c.id, "nombre": c.nombre, "direccion": c.direccion}
                for c in centros
            ]
        })
    
    @action(detail=True, methods=['get'])
    def estadisticas_asistencia(self, request, pk=None):
        """Obtener estadísticas de asistencia de un paciente"""
        from apps.turnos_core.models import Turno
        
        paciente = self.get_object()
        
        # Obtener todos los turnos del paciente
        turnos = Turno.objects.filter(usuario=paciente.user)
        
        # Calcular estadísticas
        total_turnos = turnos.count()
        asistidos = turnos.filter(asistio=True).count()
        no_asistidos = turnos.filter(asistio=False).count()
        pendientes = turnos.filter(asistio__isnull=True).count()
        
        # Calcular tasa de asistencia
        turnos_marcados = asistidos + no_asistidos
        tasa_asistencia = (asistidos / turnos_marcados * 100) if turnos_marcados > 0 else 0
        
        return Response({
            "total_turnos": total_turnos,
            "asistidos": asistidos,
            "no_asistidos": no_asistidos,
            "pendientes": pendientes,
            "tasa_asistencia": round(tasa_asistencia, 2)
        })
    
    @action(detail=True, methods=['get'])
    def historial_categorias(self, request, pk=None):
        """Obtener historial de cambios de categoría de un paciente"""
        from apps.ethe_medica.models import HistorialCategoria
        
        paciente = self.get_object()
        historial = HistorialCategoria.objects.filter(paciente=paciente).order_by('-fecha_cambio')
        
        # Serializar historial
        historial_data = []
        for item in historial:
            historial_data.append({
                "id": item.id,
                "categoria_anterior": item.categoria_anterior,
                "categoria_nueva": item.categoria_nueva,
                "motivo": item.motivo,
                "fecha_cambio": item.fecha_cambio,
                "medico": {
                    "id": item.medico.id,
                    "nombre": item.medico.user.nombre,
                    "apellido": item.medico.user.apellido
                } if item.medico else None,
                "test_resultado": {
                    "id": item.test_resultado.id,
                    "tipo_test": item.test_resultado.tipo_test,
                    "resultado": item.test_resultado.resultado
                } if item.test_resultado else None
            })
        
        return Response(historial_data)
    
    @action(detail=True, methods=['get'], url_path='seguimiento-completo')
    def seguimiento_completo(self, request, pk=None):
        """Obtener historial completo del paciente (timeline de eventos)"""
        paciente = self.get_object()
        
        # Verificar permisos: Admin ministro puede ver cualquier paciente
        # Médicos solo pueden ver pacientes que atendieron
        user = request.user
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        if rol_actual not in ['admin_ministro_salud', 'admin_ministro'] and not user.is_super_admin:
            # Verificar que el médico haya atendido al paciente
            if hasattr(user, 'medico_ethe'):
                medico = user.medico_ethe
                # Verificar si hay alguna relación entre médico y paciente
                es_su_paciente = (
                    paciente.medico_ingreso == medico or
                    ResultadoTest.objects.filter(paciente=paciente, medico=medico).exists() or
                    SeguimientoPaciente.objects.filter(paciente=paciente).exists()
                )
                if not es_su_paciente:
                    return Response({"error": "No tiene permisos para ver este paciente"}, status=403)
        
        # Construir timeline de eventos
        eventos = []
        
        # 1. Ingreso del paciente
        eventos.append({
            "tipo": "INGRESO",
            "fecha": paciente.fecha_ingreso,
            "descripcion": f"Paciente ingresado al sistema. Categoría inicial: {paciente.categoria_actual}",
            "medico": {
                "nombre": paciente.medico_ingreso.user.nombre if paciente.medico_ingreso else None,
                "apellido": paciente.medico_ingreso.user.apellido if paciente.medico_ingreso else None
            } if paciente.medico_ingreso else None,
            "centro": paciente.centro_ingreso.nombre if paciente.centro_ingreso else None
        })
        
        # 2. Tests realizados
        tests = ResultadoTest.objects.filter(paciente=paciente).order_by('fecha_realizacion')
        for test in tests:
            eventos.append({
                "tipo": "TEST",
                "subtipo": test.tipo_test,
                "fecha": test.fecha_realizacion,
                "descripcion": f"Test {test.tipo_test} realizado. Resultado: {test.resultado}",
                "medico": {
                    "nombre": test.medico.user.nombre if test.medico else None,
                    "apellido": test.medico.user.apellido if test.medico else None
                } if test.medico else None,
                "centro": test.centro.nombre if test.centro else None,
                "detalles": {
                    "tipo_test": test.tipo_test,
                    "resultado": test.resultado,
                    "notas": test.observaciones
                }
            })
        
        # 3. Cambios de categoría (derivaciones)
        from apps.ethe_medica.models import HistorialCategoria
        cambios = HistorialCategoria.objects.filter(paciente=paciente).order_by('fecha_cambio')
        for cambio in cambios:
            eventos.append({
                "tipo": "DERIVACION",
                "fecha": cambio.fecha_cambio,
                "descripcion": f"Derivación de {cambio.categoria_anterior} a {cambio.categoria_nueva}",
                "medico": {
                    "nombre": cambio.medico.user.nombre if cambio.medico else None,
                    "apellido": cambio.medico.user.apellido if cambio.medico else None
                } if cambio.medico else None,
                "detalles": {
                    "categoria_anterior": cambio.categoria_anterior,
                    "categoria_nueva": cambio.categoria_nueva,
                    "motivo": cambio.motivo
                }
            })
        
        # 4. Seguimientos/Consultas
        seguimientos = SeguimientoPaciente.objects.filter(paciente=paciente).order_by('fecha_programada')
        for seg in seguimientos:
            if seg.estado == 'REALIZADO':
                eventos.append({
                    "tipo": "CONSULTA",
                    "fecha": seg.fecha_realizado or seg.fecha_programada,
                    "descripcion": f"Consulta de seguimiento realizada",
                    "detalles": {
                        "protocolo": seg.protocolo.nombre if seg.protocolo else None,
                        "observaciones": seg.observaciones
                    }
                })
        
        # 5. Turnos (historial de asistencia)
        from apps.turnos_core.models import Turno
        turnos = Turno.objects.filter(usuario=paciente.user).order_by('fecha', 'hora')
        for turno in turnos:
            if turno.asistio is not None:
                eventos.append({
                    "tipo": "TURNO",
                    "fecha": timezone.datetime.combine(turno.fecha, turno.hora),
                    "descripcion": f"Turno {'asistido' if turno.asistio else 'no asistido'}",
                    "detalles": {
                        "lugar": turno.lugar.nombre if turno.lugar else None,
                        "asistio": turno.asistio,
                        "observaciones": getattr(turno, 'observaciones_asistencia', '')
                    }
                })
        
        # Ordenar eventos por fecha
        eventos.sort(key=lambda x: x['fecha'])
        
        # Datos generales del paciente
        paciente_data = {
            "id": paciente.id,
            "nombre": paciente.user.nombre,
            "apellido": paciente.user.apellido,
            "documento": paciente.documento,
            "email": paciente.user.email,
            "telefono": paciente.telefono_contacto,
            "fecha_nacimiento": paciente.fecha_nacimiento,
            "categoria_actual": paciente.categoria_actual,
            "activo": paciente.activo,
            "fecha_ingreso": paciente.fecha_ingreso,
            "medico_ingreso": {
                "nombre": paciente.medico_ingreso.user.nombre if paciente.medico_ingreso else None,
                "apellido": paciente.medico_ingreso.user.apellido if paciente.medico_ingreso else None
            } if paciente.medico_ingreso else None
        }
        
        return Response({
            "paciente": paciente_data,
            "historial_eventos": eventos,
            "estadisticas": {
                "total_tests": tests.count(),
                "total_consultas": seguimientos.filter(estado='REALIZADO').count(),
                "total_turnos": turnos.count(),
                "turnos_asistidos": turnos.filter(asistio=True).count()
            }
        })


class ResultadoTestViewSet(viewsets.ModelViewSet):
    """ViewSet para resultados de tests"""
    serializer_class = ResultadoTestSerializer
    permission_classes = [PuedeRegistrarTests]
    filterset_fields = ['tipo_test', 'resultado', 'centro', 'medico']
    
    def get_queryset(self):
        """Filtrar tests según rol del usuario"""
        user = self.request.user
        
        if user.is_super_admin:
            return ResultadoTest.objects.all()
        
        # Médicos ven tests que realizaron
        if hasattr(user, "medico_ethe"):
            return ResultadoTest.objects.filter(medico=user.medico_ethe)
        
        # Pacientes ven sus propios tests
        if hasattr(user, "paciente_ethe"):
            return ResultadoTest.objects.filter(paciente=user.paciente_ethe)
        
        # Admins ven tests de su cliente
        return ResultadoTest.objects.filter(centro__cliente=user.cliente)


class EstablecimientoViewSet(viewsets.ModelViewSet):
    """ViewSet para establecimientos"""
    serializer_class = EstablecimientoSerializer
    permission_classes = [PuedeGestionarCentros]
    filterset_fields = ['activo']
    search_fields = ['nombre', 'direccion']
    
    def get_queryset(self):
        """Filtrar establecimientos por cliente"""
        user = self.request.user
        if user.is_super_admin:
            return Establecimiento.objects.all()
        
        return Establecimiento.objects.filter(cliente=user.cliente)


class CentroAtencionViewSet(viewsets.ModelViewSet):
    """ViewSet para centros de atención"""
    serializer_class = CentroAtencionSerializer
    permission_classes = []  # Sin permisos para debugging
    # filterset_fields = ['establecimiento', 'activo']
    # search_fields = ['nombre_centro', 'establecimiento__nombre']
    
    def get_queryset(self):
        """Filtrar centros por cliente"""
        # Por ahora, devolver todos los centros para debugging
        return CentroAtencion.objects.all()


class JerarquiaCentroViewSet(viewsets.ModelViewSet):
    """ViewSet para jerarquías de centros"""
    serializer_class = JerarquiaCentroSerializer
    permission_classes = [PuedeGestionarAsignaciones]
    filterset_fields = ['centro_origen', 'centro_destino', 'activo']
    
    def get_queryset(self):
        """Filtrar jerarquías por cliente"""
        user = self.request.user
        if user.is_super_admin:
            return JerarquiaCentro.objects.all()
        
        return JerarquiaCentro.objects.filter(
            centro_origen__establecimiento__cliente=user.cliente
        )


class ProtocoloSeguimientoViewSet(viewsets.ModelViewSet):
    """ViewSet para protocolos de seguimiento"""
    serializer_class = ProtocoloSeguimientoSerializer
    permission_classes = [PuedeGestionarProtocolos]
    
    def get_queryset(self):
        return ProtocoloSeguimiento.objects.all()


class SeguimientoPacienteViewSet(viewsets.ModelViewSet):
    """ViewSet para seguimientos de pacientes"""
    serializer_class = SeguimientoPacienteSerializer
    permission_classes = [PuedeVerPacientes]
    filterset_fields = ['estado', 'paciente', 'protocolo']
    
    def get_queryset(self):
        """Filtrar seguimientos según rol del usuario"""
        user = self.request.user
        
        if user.is_super_admin:
            return SeguimientoPaciente.objects.all()
        
        # Pacientes ven sus propios seguimientos
        if hasattr(user, "paciente_ethe"):
            return SeguimientoPaciente.objects.filter(paciente=user.paciente_ethe)
        
        # Médicos y admins ven seguimientos de su cliente
        return SeguimientoPaciente.objects.filter(
            paciente__user__cliente=user.cliente
        )


class DashboardView(APIView):
    """Vista para dashboard con estadísticas"""
    permission_classes = [PuedeVerEstadisticas]
    
    def get(self, request):
        """Obtener estadísticas generales"""
        user = request.user
        
        # Filtrar por cliente si no es super admin
        if user.is_super_admin:
            pacientes_qs = Paciente.objects.all()
            tests_qs = ResultadoTest.objects.all()
            seguimientos_qs = SeguimientoPaciente.objects.all()
        else:
            pacientes_qs = Paciente.objects.filter(user__cliente=user.cliente)
            tests_qs = ResultadoTest.objects.filter(centro__cliente=user.cliente)
            seguimientos_qs = SeguimientoPaciente.objects.filter(
                paciente__user__cliente=user.cliente
            )
        
        # Estadísticas básicas
        total_pacientes = pacientes_qs.count()
        
        # Pacientes por categoría
        pacientes_por_categoria = dict(
            pacientes_qs.values_list('categoria_actual').annotate(
                count=Count('id')
            )
        )
        
        # Tests realizados este mes
        mes_actual = timezone.now().date().replace(day=1)
        tests_mes = tests_qs.filter(
            fecha_realizacion__gte=mes_actual
        ).values('tipo_test').annotate(count=Count('id'))
        
        tests_realizados_mes = {item['tipo_test']: item['count'] for item in tests_mes}
        
        # Centros activos
        centros_activos = pacientes_qs.values_list('centro_ingreso', flat=True).distinct().count()
        
        # Médicos activos
        medicos_activos = tests_qs.values_list('medico', flat=True).distinct().count()
        
        # Seguimientos pendientes
        seguimientos_pendientes = seguimientos_qs.filter(
            estado="PENDIENTE",
            fecha_programada__lte=timezone.now().date()
        ).count()
        
        # Tasa de asistencia
        seguimientos_realizados = seguimientos_qs.filter(estado="REALIZADO").count()
        total_seguimientos = seguimientos_qs.count()
        tasa_asistencia = (seguimientos_realizados / total_seguimientos * 100) if total_seguimientos > 0 else 0
        
        estadisticas = {
            "total_pacientes": total_pacientes,
            "pacientes_por_categoria": pacientes_por_categoria,
            "tests_realizados_mes": tests_realizados_mes,
            "centros_activos": centros_activos,
            "medicos_activos": medicos_activos,
            "seguimientos_pendientes": seguimientos_pendientes,
            "tasa_asistencia": round(tasa_asistencia, 2)
        }
        
        serializer = EstadisticasSerializer(estadisticas)
        return Response(serializer.data)


class ReservarTurnoView(APIView):
    """Vista para reservar turno de paciente"""
    permission_classes = [EsMedicoCualquiera]
    
    def post(self, request):
        """Reservar turno para paciente"""
        serializer = ReservarTurnoSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        turno = serializer.save()
        
        return Response({
            "message": "Turno reservado exitosamente",
            "turno_id": turno.id,
            "fecha": turno.fecha,
            "hora": turno.hora,
            "centro": turno.lugar.nombre
        }, status=status.HTTP_201_CREATED)


class DashboardMedicoC1View(APIView):
    """Dashboard específico para médicos C1"""
    permission_classes = [EsMedicoC1]
    
    def get(self, request):
        """Estadísticas para médico C1"""
        user = request.user
        
        try:
            medico = user.medico_ethe
        except:
            return Response({"error": "Usuario no es médico C1"}, status=400)
        
        # Fecha actual y mes actual
        hoy = timezone.now().date()
        mes_actual = hoy.replace(day=1)
        
        # Pacientes ingresados por este médico
        pacientes_qs = Paciente.objects.filter(medico_ingreso=medico)
        
        # Estadísticas
        pacientes_hoy = pacientes_qs.filter(fecha_ingreso__date=hoy).count()
        pacientes_mes = pacientes_qs.filter(fecha_ingreso__gte=mes_actual).count()
        
        # Tests POCUS realizados este mes
        tests_pocus = ResultadoTest.objects.filter(
            medico=medico,
            tipo_test='POCUS',
            fecha_realizacion__gte=mes_actual
        ).count()
        
        # Derivaciones a C2 este mes (pacientes que cambiaron a C2)
        from apps.ethe_medica.models import HistorialCategoria
        derivaciones_c2 = HistorialCategoria.objects.filter(
            medico=medico,
            categoria_nueva='C2',
            fecha_cambio__gte=mes_actual
        ).count()
        
        return Response({
            "pacientesHoy": pacientes_hoy,
            "pacientesMes": pacientes_mes,
            "testsPocus": tests_pocus,
            "derivacionesC2": derivaciones_c2
        })


class DashboardMedicoC2View(APIView):
    """Dashboard específico para médicos C2"""
    permission_classes = [EsMedicoC2]
    
    def get(self, request):
        """Estadísticas para médico C2"""
        user = request.user
        
        try:
            medico = user.medico_ethe
        except:
            return Response({"error": "Usuario no es médico C2"}, status=400)
        
        # Fecha actual y mes actual
        hoy = timezone.now().date()
        mes_actual = hoy.replace(day=1)
        
        # Pacientes C2 del médico
        pacientes_c2 = Paciente.objects.filter(categoria_actual='C2')
        
        # Tests FIBROSCAN realizados por este médico
        fibroscan_mes = ResultadoTest.objects.filter(
            medico=medico,
            tipo_test='FIBROSCAN',
            fecha_realizacion__gte=mes_actual
        ).count()
        
        # Derivaciones a C3 este mes
        from apps.ethe_medica.models import HistorialCategoria
        derivaciones_c3 = HistorialCategoria.objects.filter(
            medico=medico,
            categoria_nueva='C3',
            fecha_cambio__gte=mes_actual
        ).count()
        
        # Pacientes C2 atendidos hoy (turnos de hoy)
        from apps.turnos_core.models import Turno
        prestador = medico.prestador
        turnos_hoy = Turno.objects.filter(
            object_id=prestador.id,
            fecha=hoy
        ).count()
        
        # Pacientes C2 activos
        pacientes_c2_activos = pacientes_c2.filter(activo=True).count()
        
        return Response({
            "pacientesC2Hoy": turnos_hoy,
            "fibroscanRealizadosMes": fibroscan_mes,
            "derivacionesC3Mes": derivaciones_c3,
            "pacientesC2Activos": pacientes_c2_activos
        })


class DashboardMedicoC3View(APIView):
    """Dashboard específico para médicos C3"""
    permission_classes = [EsMedicoC3]
    
    def get(self, request):
        """Estadísticas para médico C3"""
        user = request.user
        
        try:
            medico = user.medico_ethe
        except:
            return Response({"error": "Usuario no es médico C3"}, status=400)
        
        # Fecha actual y mes actual
        hoy = timezone.now().date()
        mes_actual = hoy.replace(day=1)
        
        # Pacientes C3
        pacientes_c3 = Paciente.objects.filter(categoria_actual='C3')
        pacientes_c3_activos = pacientes_c3.filter(activo=True).count()
        
        # Turnos hoy del médico
        from apps.turnos_core.models import Turno
        prestador = medico.prestador
        turnos_hoy = Turno.objects.filter(
            object_id=prestador.id,
            fecha=hoy
        ).count()
        
        # Seguimientos realizados este mes (aproximación de consultas)
        consultas_mes = SeguimientoPaciente.objects.filter(
            estado='REALIZADO',
            fecha_realizada__gte=mes_actual
        ).count()
        
        # Altas médicas este mes (pacientes que dejaron de estar activos)
        # Por ahora usar un estimado
        altas_mes = 0  # TODO: Implementar lógica de altas
        
        return Response({
            "pacientesC3Hoy": turnos_hoy,
            "tratamientosIniciadosMes": 0,  # TODO: Implementar cuando exista modelo Tratamiento
            "altasMedicasMes": altas_mes,
            "pacientesC3Activos": pacientes_c3_activos
        })


class DashboardEstablecimientoView(APIView):
    """Dashboard para admin de establecimiento"""
    permission_classes = [EsAdminEstablecimiento]
    
    def get(self, request):
        """Estadísticas del establecimiento"""
        user = request.user
        
        # Obtener establecimiento del admin
        # Asumiendo que el admin_establecimiento está vinculado al establecimiento
        try:
            establecimiento = Establecimiento.objects.get(admin_establecimiento=user)
        except Establecimiento.DoesNotExist:
            return Response({"error": "Usuario no administra ningún establecimiento"}, status=400)
        
        # Médicos del establecimiento
        from apps.turnos_core.models import Lugar
        centros = CentroAtencion.objects.filter(establecimiento=establecimiento)
        lugares_ids = centros.values_list('lugar_id', flat=True)
        
        # Médicos que tienen disponibilidad en estos lugares
        from apps.turnos_core.models import Disponibilidad
        medicos_ids = Disponibilidad.objects.filter(
            lugar_id__in=lugares_ids,
            activo=True
        ).values_list('prestador__medico_ethe__id', flat=True).distinct()
        
        total_medicos = len(set(medicos_ids))
        medicos_activos = Medico.objects.filter(id__in=medicos_ids, activo=True).count()
        
        # Pacientes del establecimiento
        pacientes = Paciente.objects.filter(centro_ingreso_id__in=lugares_ids)
        total_pacientes = pacientes.count()
        
        # Turnos de hoy
        from apps.turnos_core.models import Turno
        hoy = timezone.now().date()
        turnos_hoy = Turno.objects.filter(
            lugar_id__in=lugares_ids,
            fecha=hoy
        )
        
        turnos_hoy_count = turnos_hoy.count()
        turnos_confirmados = turnos_hoy.filter(estado='CONFIRMADO').count()
        turnos_completados = turnos_hoy.filter(asistio=True).count()
        
        # Tasa de asistencia
        turnos_marcados = turnos_hoy.filter(asistio__isnull=False).count()
        tasa_asistencia = (turnos_completados / turnos_marcados * 100) if turnos_marcados > 0 else 0
        
        return Response({
            "total_medicos": total_medicos,
            "medicos_activos": medicos_activos,
            "total_pacientes": total_pacientes,
            "turnos_hoy": turnos_hoy_count,
            "turnos_confirmados": turnos_confirmados,
            "turnos_completados": turnos_completados,
            "tasa_asistencia": round(tasa_asistencia, 2)
        })


class DashboardMinistroView(APIView):
    """Dashboard para admin ministro (vista completa del sistema)"""
    permission_classes = [EsAdminMinistroSalud]
    
    def get(self, request):
        """Estadísticas generales del sistema para el ministro"""
        user = request.user
        
        # Fecha actual y mes actual
        mes_actual = timezone.now().date().replace(day=1)
        
        # Filtrar por cliente si no es super admin
        if user.is_super_admin:
            establecimientos_qs = Establecimiento.objects.all()
            pacientes_qs = Paciente.objects.all()
            medicos_qs = Medico.objects.all()
            tests_qs = ResultadoTest.objects.all()
        else:
            establecimientos_qs = Establecimiento.objects.filter(cliente=user.cliente)
            pacientes_qs = Paciente.objects.filter(user__cliente=user.cliente)
            medicos_qs = Medico.objects.filter(user__cliente=user.cliente)
            tests_qs = ResultadoTest.objects.filter(centro__cliente=user.cliente)
        
        # Estadísticas de establecimientos
        total_establecimientos = establecimientos_qs.count()
        establecimientos_activos = establecimientos_qs.filter(activo=True).count()
        
        # Estadísticas de pacientes
        total_pacientes = pacientes_qs.count()
        pacientes_activos = pacientes_qs.filter(activo=True).count()
        
        # Pacientes por categoría
        pacientes_c1 = pacientes_qs.filter(categoria_actual='C1').count()
        pacientes_c2 = pacientes_qs.filter(categoria_actual='C2').count()
        pacientes_c3 = pacientes_qs.filter(categoria_actual='C3').count()
        
        # Estadísticas de médicos
        total_medicos = medicos_qs.count()
        medicos_activos = medicos_qs.filter(activo=True).count()
        
        # Turnos del mes
        from apps.turnos_core.models import Turno
        turnos_mes = Turno.objects.filter(fecha__gte=mes_actual).count()
        
        # Tasa de asistencia general
        turnos_marcados = Turno.objects.filter(
            fecha__gte=mes_actual,
            asistio__isnull=False
        )
        turnos_asistidos = turnos_marcados.filter(asistio=True).count()
        total_marcados = turnos_marcados.count()
        tasa_asistencia = (turnos_asistidos / total_marcados * 100) if total_marcados > 0 else 0
        
        # Nuevos ingresos del mes
        nuevos_ingresos = pacientes_qs.filter(fecha_ingreso__gte=mes_actual).count()
        
        # Derivaciones del mes
        from apps.ethe_medica.models import HistorialCategoria
        derivaciones_c2 = HistorialCategoria.objects.filter(
            categoria_nueva='C2',
            fecha_cambio__gte=mes_actual
        ).count()
        
        derivaciones_c3 = HistorialCategoria.objects.filter(
            categoria_nueva='C3',
            fecha_cambio__gte=mes_actual
        ).count()
        
        # Tests realizados este mes
        tests_mes = tests_qs.filter(fecha_realizacion__gte=mes_actual)
        tests_pocus = tests_mes.filter(tipo_test='POCUS').count()
        tests_fib4 = tests_mes.filter(tipo_test='FIB4').count()
        tests_fibroscan = tests_mes.filter(tipo_test='FIBROSCAN').count()
        
        return Response({
            "total_establecimientos": total_establecimientos,
            "establecimientos_activos": establecimientos_activos,
            "total_pacientes": total_pacientes,
            "pacientes_activos": pacientes_activos,
            "pacientes_c1": pacientes_c1,
            "pacientes_c2": pacientes_c2,
            "pacientes_c3": pacientes_c3,
            "pacientes_por_categoria": {
                "C1": pacientes_c1,
                "C2": pacientes_c2,
                "C3": pacientes_c3
            },
            "total_medicos": total_medicos,
            "medicos_activos": medicos_activos,
            "turnos_mes": turnos_mes,
            "tasa_asistencia_general": round(tasa_asistencia, 2),
            "nuevos_ingresos_mes": nuevos_ingresos,
            "derivaciones_c2_mes": derivaciones_c2,
            "derivaciones_c3_mes": derivaciones_c3,
            "tests_realizados_mes": {
                "POCUS": tests_pocus,
                "FIB4": tests_fib4,
                "FIBROSCAN": tests_fibroscan
            }
        })


class EstablecimientosMinistroView(APIView):
    """Gestión de establecimientos para admin ministro"""
    permission_classes = [EsAdminMinistroSalud]

    def get(self, request):
        """Listar todos los establecimientos"""
        establecimientos = Establecimiento.objects.filter(cliente=request.user.cliente)
        data = []
        for est in establecimientos:
            data.append({
                "id": est.id,
                "nombre": est.nombre,
                "direccion": est.direccion,
                "telefono": est.telefono,
                "email": est.email,
                "activo": est.activo,
                "admin_establecimiento": {
                    "id": est.admin_establecimiento.id,
                    "nombre": est.admin_establecimiento.get_full_name(),
                    "email": est.admin_establecimiento.email
                } if est.admin_establecimiento else None,
                "medicos_count": 0,  # TODO: Implementar relación con médicos
                "pacientes_count": 0  # TODO: Implementar relación con pacientes
            })
        return Response(data)

    def post(self, request):
        """Crear nuevo establecimiento"""
        data = request.data
        establecimiento = Establecimiento.objects.create(
            nombre=data.get('nombre'),
            direccion=data.get('direccion', ''),
            telefono=data.get('telefono', ''),
            email=data.get('email', ''),
            cliente=request.user.cliente,
            activo=True
        )
        return Response({
            "id": establecimiento.id,
            "nombre": establecimiento.nombre,
            "direccion": establecimiento.direccion,
            "telefono": establecimiento.telefono,
            "email": establecimiento.email,
            "activo": establecimiento.activo
        }, status=201)


class CrearAdminEstablecimientoView(APIView):
    """Crear admin de establecimiento"""
    permission_classes = [EsAdminMinistroSalud]

    def post(self, request):
        """Crear un nuevo admin de establecimiento"""
        from django.contrib.auth import get_user_model
        from apps.auth_core.models import UserClient
        
        User = get_user_model()
        data = request.data
        
        # Crear usuario
        user = User.objects.create_user(
            username=data['email'],
            email=data['email'],
            password=data['password'],
            nombre=data['nombre'],
            apellido=data['apellido'],
            cliente=request.user.cliente
        )
        
        # Crear UserClient con rol admin_establecimiento
        user_client = UserClient.objects.create(
            usuario=user,
            cliente=request.user.cliente,
            rol='admin_establecimiento'
        )
        
        return Response({
            "id": user.id,
            "nombre": user.get_full_name(),
            "email": user.email,
            "rol": user_client.rol
        }, status=201)


class AsignarAdminEstablecimientoView(APIView):
    """Asignar admin a establecimiento"""
    permission_classes = [EsAdminMinistroSalud]

    def post(self, request, establecimiento_id):
        """Asignar admin a establecimiento"""
        try:
            establecimiento = Establecimiento.objects.get(
                id=establecimiento_id,
                cliente=request.user.cliente
            )
            admin_id = request.data.get('admin_id')
            
            if admin_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admin = User.objects.get(id=admin_id, cliente=request.user.cliente)
                establecimiento.admin_establecimiento = admin
                establecimiento.save()
            else:
                establecimiento.admin_establecimiento = None
                establecimiento.save()
            
            return Response({
                "message": "Admin asignado correctamente",
                "establecimiento": {
                    "id": establecimiento.id,
                    "nombre": establecimiento.nombre,
                    "admin": {
                        "id": establecimiento.admin_establecimiento.id,
                        "nombre": establecimiento.admin_establecimiento.get_full_name(),
                        "email": establecimiento.admin_establecimiento.email
                    } if establecimiento.admin_establecimiento else None
                }
            })
        except Establecimiento.DoesNotExist:
            return Response({"error": "Establecimiento no encontrado"}, status=404)
        except User.DoesNotExist:
            return Response({"error": "Admin no encontrado"}, status=404)


class CentrosDisponiblesView(APIView):
    """Listar centros disponibles para derivación"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Obtener centros disponibles por categoría"""
        # Verificar permisos
        from apps.auth_core.utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        # Verificar si es médico o admin ministro
        es_medico = False
        if hasattr(request.user, 'medico_ethe'):
            medico = request.user.medico_ethe
            es_medico = medico.tiene_categoria("C1") or medico.tiene_categoria("C2") or medico.tiene_categoria("C3")
        
        es_admin_ministro = rol_actual == "admin_ministro_salud"
        
        if not es_medico and not es_admin_ministro:
            return Response({
                "error": "No tiene permisos para acceder a este endpoint"
            }, status=403)
        
        categoria = request.query_params.get('categoria')
        centro_actual_id = request.query_params.get('centro_actual_id')
        
        if not categoria or not centro_actual_id:
            return Response({
                "error": "Los parámetros 'categoria' y 'centro_actual_id' son obligatorios"
            }, status=400)
        
        # Validar categoría
        if categoria not in ['C1', 'C2', 'C3']:
            return Response({
                "error": "Categoría debe ser C1, C2 o C3"
            }, status=400)
        
        try:
            # Obtener centro actual
            centro_actual = CentroAtencion.objects.get(
                id=centro_actual_id,
                establecimiento__cliente=request.user.cliente
            )
        except CentroAtencion.DoesNotExist:
            return Response({
                "error": "Centro actual no encontrado"
            }, status=404)
        
        # Buscar centros disponibles según jerarquía
        centros_disponibles = []
        
        if categoria == 'C2':
            # C1 → C2
            jerarquias = JerarquiaCentro.objects.filter(
                centro_origen=centro_actual,
                categoria_destino='C2',
                activo=True
            ).select_related('centro_destino', 'centro_destino__lugar', 'centro_destino__establecimiento')
            
            for jerarquia in jerarquias:
                centro_destino = jerarquia.centro_destino
                if centro_destino.puede_atender_categoria('C2'):
                    centros_disponibles.append({
                        "centro_id": centro_destino.id,
                        "centro_nombre": centro_destino.nombre_centro,
                        "establecimiento": centro_destino.establecimiento.nombre,
                        "lugar_id": centro_destino.lugar.id,
                        "direccion": centro_destino.lugar.direccion,
                        "telefono": centro_destino.lugar.telefono,
                        "prioridad": jerarquia.prioridad,
                        "distancia_km": float(jerarquia.distancia_km) if jerarquia.distancia_km else None
                    })
        
        elif categoria == 'C3':
            # C2 → C3
            jerarquias = JerarquiaCentro.objects.filter(
                centro_origen=centro_actual,
                categoria_destino='C3',
                activo=True
            ).select_related('centro_destino', 'centro_destino__lugar', 'centro_destino__establecimiento')
            
            for jerarquia in jerarquias:
                centro_destino = jerarquia.centro_destino
                if centro_destino.puede_atender_categoria('C3'):
                    centros_disponibles.append({
                        "centro_id": centro_destino.id,
                        "centro_nombre": centro_destino.nombre_centro,
                        "establecimiento": centro_destino.establecimiento.nombre,
                        "lugar_id": centro_destino.lugar.id,
                        "direccion": centro_destino.lugar.direccion,
                        "telefono": centro_destino.lugar.telefono,
                        "prioridad": jerarquia.prioridad,
                        "distancia_km": float(jerarquia.distancia_km) if jerarquia.distancia_km else None
                    })
        
        # Ordenar por prioridad (mayor a menor)
        centros_disponibles.sort(key=lambda x: x['prioridad'], reverse=True)
        
        return Response({
            "centros_disponibles": centros_disponibles,
            "categoria_solicitada": categoria,
            "centro_actual": {
                "id": centro_actual.id,
                "nombre": centro_actual.nombre_centro,
                "establecimiento": centro_actual.establecimiento.nombre
            }
        })


class CentrosSuperioresView(APIView):
    """Listar centros superiores para derivación con médicos y turnos"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Obtener centros superiores con médicos y turnos disponibles"""
        # Verificar permisos - solo médicos pueden derivar
        if not hasattr(request.user, 'medico_ethe'):
            return Response({
                "error": "Solo los médicos pueden acceder a este endpoint"
            }, status=403)
        
        centro_actual_id = request.query_params.get('centro_actual_id')
        
        if not centro_actual_id:
            return Response({
                "error": "El parámetro 'centro_actual_id' es obligatorio"
            }, status=400)
        
        try:
            # Obtener centro actual
            centro_actual = CentroAtencion.objects.get(id=centro_actual_id)
        except CentroAtencion.DoesNotExist:
            return Response({
                "error": "Centro actual no encontrado"
            }, status=404)
        
        # Determinar categoría superior
        categorias_actuales = centro_actual.categorias
        categoria_superior = None
        
        if "C1" in categorias_actuales:
            categoria_superior = "C2"
        elif "C2" in categorias_actuales:
            categoria_superior = "C3"
        else:
            return Response({
                "error": "No hay categoría superior disponible para este centro"
            }, status=400)
        
        # DATOS MOCK PARA PRUEBAS
        centros_superiores = [
            {
                'id': 1,
                'nombre': 'Centro C2 - Gastroenterología',
                'categorias': ['C2'],
                'lugar': {
                    'id': 1,
                    'nombre': 'Centro C2 - Gastroenterología - Lugar',
                    'direccion': 'Av. Principal 123'
                },
                'establecimiento': {
                    'id': 1,
                    'nombre': 'Hospital Regional C2'
                },
                'medicos': [
                    {
                        'id': 1,
                        'nombre': 'Dr. Carlos Mendoza',
                        'especialidad': 'Gastroenterología',
                        'matricula': 'MAT-C2-001',
                        'turnos': [
                            {'id': 1, 'fecha': '2025-10-25', 'hora': '09:00', 'estado': 'disponible'},
                            {'id': 2, 'fecha': '2025-10-25', 'hora': '10:00', 'estado': 'disponible'},
                            {'id': 3, 'fecha': '2025-10-25', 'hora': '11:00', 'estado': 'disponible'},
                            {'id': 4, 'fecha': '2025-10-26', 'hora': '09:00', 'estado': 'disponible'},
                            {'id': 5, 'fecha': '2025-10-26', 'hora': '14:00', 'estado': 'disponible'}
                        ]
                    },
                    {
                        'id': 2,
                        'nombre': 'Dra. Ana Rodríguez',
                        'especialidad': 'Hepatología',
                        'matricula': 'MAT-C2-002',
                        'turnos': [
                            {'id': 6, 'fecha': '2025-10-25', 'hora': '14:00', 'estado': 'disponible'},
                            {'id': 7, 'fecha': '2025-10-25', 'hora': '15:00', 'estado': 'disponible'},
                            {'id': 8, 'fecha': '2025-10-27', 'hora': '09:00', 'estado': 'disponible'},
                            {'id': 9, 'fecha': '2025-10-27', 'hora': '10:00', 'estado': 'disponible'}
                        ]
                    }
                ]
            },
            {
                'id': 2,
                'nombre': 'Centro C2 - Hepatología Avanzada',
                'categorias': ['C2'],
                'lugar': {
                    'id': 2,
                    'nombre': 'Centro C2 - Hepatología Avanzada - Lugar',
                    'direccion': 'Calle Secundaria 456'
                },
                'establecimiento': {
                    'id': 2,
                    'nombre': 'Centro Médico Especializado C2'
                },
                'medicos': [
                    {
                        'id': 3,
                        'nombre': 'Dr. Luis Fernández',
                        'especialidad': 'Cirugía Digestiva',
                        'matricula': 'MAT-C2-003',
                        'turnos': [
                            {'id': 10, 'fecha': '2025-10-25', 'hora': '16:00', 'estado': 'disponible'},
                            {'id': 11, 'fecha': '2025-10-28', 'hora': '09:00', 'estado': 'disponible'},
                            {'id': 12, 'fecha': '2025-10-28', 'hora': '11:00', 'estado': 'disponible'}
                        ]
                    }
                ]
            }
        ]
        
        return Response({
            "centro_actual": {
                "id": centro_actual.id,
                "nombre": centro_actual.nombre_centro,
                "categorias": centro_actual.categorias
            },
            "categoria_superior": categoria_superior,
            "centros_superiores": centros_superiores
        })


class ReservarTurnoDerivacionView(APIView):
    """Reservar turno en nombre del paciente para derivación"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Reservar turno para derivación de paciente"""
        # Verificar permisos - solo médicos pueden derivar
        if not hasattr(request.user, 'medico_ethe'):
            return Response({
                "error": "Solo los médicos pueden acceder a este endpoint"
            }, status=403)
        
        medico_derivador = request.user.medico_ethe
        
        # Validar datos requeridos
        turno_id = request.data.get('turno_id')
        paciente_id = request.data.get('paciente_id')
        motivo_derivacion = request.data.get('motivo_derivacion', '')
        
        if not turno_id or not paciente_id:
            return Response({
                "error": "Los campos 'turno_id' y 'paciente_id' son obligatorios"
            }, status=400)
        
        try:
            # Obtener el turno
            from apps.turnos_core.models import Turno
            turno = Turno.objects.get(
                id=turno_id,
                estado='disponible'
            )
        except Turno.DoesNotExist:
            return Response({
                "error": "Turno no encontrado o no disponible"
            }, status=404)
        
        try:
            # Obtener el paciente
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            return Response({
                "error": "Paciente no encontrado"
            }, status=404)
        
        # Verificar que el médico derivador puede derivar a este paciente
        # (por ejemplo, que el paciente esté bajo su cuidado)
        # TODO: Implementar validación de médico de ingreso
        # if paciente.medico_ingreso != medico_derivador:
        #     return Response({
        #         "error": "No puede derivar a este paciente"
        #     }, status=403)
        
        # Verificar que el turno es de un médico de categoría superior
        try:
            from django.contrib.contenttypes.models import ContentType
            from apps.turnos_core.models import Prestador
            
            if turno.content_type.model != 'prestador':
                return Response({
                    "error": "El turno no pertenece a un prestador"
                }, status=400)
            
            prestador = Prestador.objects.get(id=turno.object_id)
            medico_turno = prestador.medico_ethe
        except:
            return Response({
                "error": "El turno no pertenece a un médico ETHE"
            }, status=400)
        
        # Verificar jerarquía de categorías
        categorias_derivador = medico_derivador.categorias
        categorias_medico_turno = medico_turno.categorias
        
        derivacion_valida = False
        if "C1" in categorias_derivador and "C2" in categorias_medico_turno:
            derivacion_valida = True
        elif "C2" in categorias_derivador and "C3" in categorias_medico_turno:
            derivacion_valida = True
        
        if not derivacion_valida:
            return Response({
                "error": "No puede derivar a un médico de la misma o menor categoría"
            }, status=400)
        
        # Reservar el turno usando la API de turnos_core
        from django.db import transaction
        with transaction.atomic():
            # Usar la API de turnos_core para reservar
            from apps.turnos_core.views import ReservarTurnoAdminView
            from rest_framework.test import APIRequestFactory
            
            # Crear request interno para la API de turnos
            factory = APIRequestFactory()
            turnos_request = factory.post('/turnos/admin/reservar/', {
                'turno_id': turno_id,
                'usuario_id': paciente.user.id,
                'omitir_bloqueo_abono': True  # Para derivaciones médicas
            })
            turnos_request.user = request.user
            
            # Llamar a la API de turnos
            turnos_view = ReservarTurnoAdminView()
            turnos_response = turnos_view.post(turnos_request)
            
            if turnos_response.status_code != 200:
                return Response({
                    "error": f"Error al reservar turno: {turnos_response.data.get('detail', 'Error desconocido')}"
                }, status=turnos_response.status_code)
            
            # Actualizar la categoría del paciente si es necesario
            if "C1" in categorias_derivador and "C2" in categorias_medico_turno:
                paciente.categoria_actual = "C2"
            elif "C2" in categorias_derivador and "C3" in categorias_medico_turno:
                paciente.categoria_actual = "C3"
            
            # Actualizar historial de categorías
            from datetime import datetime
            paciente.historial_categorias.append({
                'categoria': paciente.categoria_actual,
                'fecha': datetime.now().isoformat(),
                'motivo': f'Derivación a {medico_turno.user.nombre} {medico_turno.user.apellido}'
            })
            paciente.save()
            
            # Crear registro de derivación
            from apps.ethe_medica.models import SeguimientoPaciente
            SeguimientoPaciente.objects.create(
                paciente=paciente,
                medico=medico_derivador,
                tipo_seguimiento='derivacion',
                observaciones=f"Paciente derivado a {medico_turno.user.nombre} {medico_turno.user.apellido}. Motivo: {motivo_derivacion}",
                fecha_realizada=timezone.now().date()
            )
        
        return Response({
            "success": True,
            "message": "Turno reservado exitosamente",
            "turno": {
                "id": turno.id,
                "fecha": turno.fecha.strftime("%Y-%m-%d"),
                "hora_inicio": turno.hora.strftime("%H:%M"),
                "hora_fin": turno.hora.strftime("%H:%M"),
                "medico": f"{medico_turno.user.nombre} {medico_turno.user.apellido}",
                "especialidad": medico_turno.especialidad_medica
            },
            "paciente": {
                "id": paciente.id,
                "nombre": f"{paciente.user.nombre} {paciente.user.apellido}",
                "categoria_actual": paciente.categoria_actual
            }
        })
