# apps/turnos_core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.turnos_core.views import (
    TurnoListView,
    TurnoReservaView,
    TurnosDisponiblesView,
    LugarViewSet,
    PrestadorViewSet,
    DisponibilidadViewSet,
    GenerarTurnosView,
    prestador_actual,
    CrearBonificacionManualView,
    bonificaciones_mias,
    CancelarTurnoView,
    CancelarPorSedeAdminView,
    CancelarPorPrestadorAdminView,
    TurnosAgendaAdminView,
    ReservarTurnoAdminView,
    LiberarTurnoAdminView,
    ToggleReservadoParaAbonoView,
    eliminar_bonificacion,
    bonificaciones_usuario,
    turnos_usuario,
    marcar_asistencia_turno,
    cancelar_turnos_masivo,
)


router = DefaultRouter()
# CRUD de sedes (lugares), accesibles según cliente
router.register(r'sedes', LugarViewSet, basename='sedes')

# CRUD de prestadores (profesores)
router.register(r'prestadores', PrestadorViewSet, basename='prestadores')

# CRUD de disponibilidades horarias de los prestadores
router.register(r'disponibilidades', DisponibilidadViewSet, basename='disponibilidades')

urlpatterns = [
    # GET → lista turnos visibles para el usuario actual (según rol, filtros estado/upcoming)
    path("", TurnoListView.as_view(), name="turno-list"),

    # POST → reservar un turno (con comprobante o usando bonificación)
    path("reservar/", TurnoReservaView.as_view(), name="turno-reserva"),

    # GET → consultar turnos disponibles/reservados futuros de un prestador en una sede (opcional fecha)
    path("disponibles/", TurnosDisponiblesView.as_view(), name="turno-disponibles"),

    # POST → generar slots de turnos automáticamente a partir de disponibilidades
    path("generar/", GenerarTurnosView.as_view(), name="generar-turnos"),

    # POST → admins crean manualmente una bonificación (voucher) para un usuario
    path("bonificaciones/crear-manual/", CrearBonificacionManualView.as_view(), name="crear-bonificacion-manual"),

    # GET → bonificaciones vigentes del usuario actual
    path("bonificados/mios/", bonificaciones_mias, name="bonificaciones-mias"),

    # GET → devuelve el prestador asociado al usuario logueado (si existe)
    path("prestador/mio/", prestador_actual),

    # POST → cancelar un turno propio (si cumple política de cancelación)
    path("cancelar/", CancelarTurnoView.as_view(), name="cancelar-turno"),

    # POST → admins cancelan en masa turnos de una sede en un rango de fechas/horas
    path("admin/cancelar_por_sede/", CancelarPorSedeAdminView.as_view(), name="cancelar-por-sede"),

    # POST → admins cancelan en masa turnos de un prestador (opcional filtrar por sede y rango horario)
    path("prestadores/<int:prestador_id>/cancelar_en_rango/", CancelarPorPrestadorAdminView.as_view(), name="cancelar-por-prestador"),
    
    path("agenda/", TurnosAgendaAdminView.as_view(), name="turnos-agenda"),
    
    path("admin/reservar/", ReservarTurnoAdminView.as_view(), name="turno-admin-reservar"),
    
    path("admin/liberar/",  LiberarTurnoAdminView.as_view(),  name="turno-admin-liberar"),
    
    path("admin/marcar_reservado_para_abono/", ToggleReservadoParaAbonoView.as_view(), name="toggle-reservado-para-abono"),
    
    # Nuevos endpoints para gestión de usuarios
    path("bonificaciones/<int:bonificacion_id>/", eliminar_bonificacion, name="eliminar-bonificacion"),
    path("bonificados/usuario/<int:usuario_id>/", bonificaciones_usuario, name="bonificaciones-usuario"),
    path("usuario/<int:usuario_id>/", turnos_usuario, name="turnos-usuario"),
    
    # Endpoint para marcar asistencia (ETHE)
    path("<int:turno_id>/marcar-asistencia/", marcar_asistencia_turno, name="marcar-asistencia"),
    
    # Endpoint para cancelación masiva (ETHE)
    path("cancelar-masivo/", cancelar_turnos_masivo, name="cancelar-masivo"),
    
    # Incluye todas las rutas de los ViewSets (sedes, prestadores, disponibilidades)
    path("", include(router.urls)),
]
