# Endpoints del Proyecto Condor

Este documento resume los principales endpoints de la API organizados según los módulos del front‑end.

## Autenticación

| Método | Endpoint                     | Vista                        | Serializer                    |
|-------|------------------------------|------------------------------|-------------------------------|
| POST  | `/api/auth/registro/`        | `RegistroView`               | `RegistroSerializer`          |
| GET   | `/api/auth/yo/`              | `MiPerfilView`               | —                             |
| POST  | `/api/auth/token/`           | `CustomTokenObtainPairView`  | `CustomTokenObtainPairSerializer` |
| POST  | `/api/auth/token/refresh/`   | `TokenRefreshView`           | —                             |
| CRUD  | `/api/auth/usuarios/`        | `UsuarioViewSet`             | `UsuarioSerializer`           |

## JugadorDashboard

| Método | Endpoint                           | Vista               | Serializer              |
|-------|------------------------------------|---------------------|-------------------------|
| GET   | `/api/turnos/`                     | `TurnoListView`     | `TurnoSerializer`       |
| GET   | `/api/turnos/bonificados/mios/`    | `bonificaciones_mias` | —                       |
| POST  | `/api/turnos/cancelar/`           | `CancelarTurnoView` | `CancelarTurnoSerializer` |

## Reservar Turno

| Método | Endpoint                                                        | Vista                         | Serializer                     |
|-------|-----------------------------------------------------------------|-------------------------------|--------------------------------|
| GET   | `/api/turnos/disponibles/?prestador_id=&lugar_id=&fecha=`        | `TurnosDisponiblesView`       | `TurnoSerializer`              |
| POST  | `/api/turnos/reservar/`                                         | `TurnoReservaView`            | `TurnoReservaSerializer`       |
| GET   | `/api/turnos/sedes/`                                            | `LugarViewSet`                | `LugarSerializer`              |
| GET   | `/api/turnos/prestadores/?lugar_id=`                            | `PrestadorViewSet`            | `PrestadorDetailSerializer`    |
| GET   | `/api/turnos/prestador/mio/`                                    | `prestador_actual`            | —                              |
| GET   | `/api/padel/sedes/`                                             | `SedePadelViewSet`            | `SedePadelSerializer`          |
| GET   | `/api/padel/configuracion/{sede_id}/`                           | `ConfiguracionSedePadelViewSet` | `ConfiguracionSedePadelSerializer` |
| GET   | `/api/padel/tipos-clase/?sede_id=`                              | `TipoClasePadelViewSet`       | `TipoClasePadelSerializer`     |
