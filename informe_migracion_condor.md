# ✅ INFORME FINAL DE MIGRACIÓN Y CONTROL DE ACCESO — BACKEND CONDOR

---

## 📦 Apps migradas y modificadas

### 🧩 1. `turnos_core`
- **Se creó el modelo genérico `Prestador`** para reemplazar a `Profesor`.
- **Se movió `Disponibilidad` a `turnos_core`** como entidad genérica.
- Se agregó `BloqueoTurnos` reutilizable con `GenericForeignKey`.
- Se creó `services/turnos.py` con `generar_turnos_para_prestador()`.
- Se agregó `GenerarTurnosView` y endpoint: `POST /api/turnos/generar/`.
- Se actualizaron los `ViewSet` para `Prestador`, `Disponibilidad`, `Turno`, `Lugar`, `BloqueoTurnos`.
- Se agregaron nuevos endpoints:
  - `/api/turnos/prestadores/`
  - `/api/turnos/disponibilidades/`
  - `/api/turnos/generar/`
- Se creó un proxy temporal en `apps/turnos_padel/urls.py` con logging:
  - `/api/padel/profesores-disponibles/` redirige a `PrestadorViewSet`
  - `/api/padel/profesores/` redirige a `DisponibilidadViewSet`

---

### 🧩 2. `auth_core`
- `UsuarioViewSet` actualizado con permisos globales:
  - Solo `super_admin` y `admin_cliente` pueden ver o crear usuarios.
- `UsuarioSerializer` fuerza `cliente` del request si el creador es `admin_cliente`.
- `RegistroSerializer` fuerza el tipo `usuario_final` y elimina cualquier intento de asignar cliente.
- `MiPerfilView` y `CustomTokenObtainPairView` mantienen su acceso autenticado sin cambios.

---

### 🧩 3. `pagos_core`
- `ComprobanteView.get_queryset` filtra según tipo de usuario:
  - `super_admin`: ve todo
  - `admin_cliente`: ve comprobantes de sus usuarios
  - `empleado_cliente`: ve los turnos asignados a él como prestador
  - `usuario_final`: ve sólo sus propios comprobantes
- `ComprobanteAprobarRechazarView`:
  - Solo `super_admin` y `admin_cliente` del cliente del turno pueden aprobar o rechazar
- `ConfiguracionPagoView` y `PagosPendientesCountView`:
  - Acceso exclusivo a `super_admin` y `admin_cliente`
- `ComprobanteUploadSerializer`:
  - Refuerza validación: solo usuario del turno o admin del cliente puede cargar un comprobante
  - Remueve uso inseguro de `is_staff`

---

### 🧩 4. `clientes_core`
- `ClienteViewSet` es solo de lectura y **exclusivo para `super_admin`**
- Se aplicó `EsSuperAdmin` como permiso centralizado
- `ClienteSerializer` sin cambios

---

## 🔐 Permisos centralizados usados

Ubicados en `apps/common/permissions.py`:

- `EsSuperAdmin`
- `EsAdminDeSuCliente`
- `EsDelMismoCliente`
- `EsPrestador`

Se aplican en todos los `ViewSet` y `APIView`, garantizando:

| Tipo de usuario     | Puede ver / modificar                                               |
|---------------------|---------------------------------------------------------------------|
| `super_admin`       | TODO                                                                |
| `admin_cliente`     | Solo datos de su cliente (usuarios, prestadores, comprobantes)     |
| `empleado_cliente`  | Solo sus propios turnos y disponibilidades                          |
| `usuario_final`     | Solo sus turnos y comprobantes                                      |

---

## 🚨 Redirecciones temporales (backward compatibility)

En `apps/turnos_padel/urls.py`:
- Se agregó logging con `logger.warning(...)` cuando se acceden rutas antiguas.
- Redirige a views genéricas sin modificar el frontend actual.

---

## 🧪 Testing y siguientes pasos

- ✅ Listo para eliminar `apps/turnos_padel` cuando el frontend migre.
- 🚨 Verificar que las migraciones de DB están generadas y aplicadas.
- 🔜 Siguiente paso sugerido: migrar frontend a nuevos endpoints `/api/turnos/*`.

---

## 🗂 Archivos modificados

```
✓ apps/turnos_core/models.py
✓ apps/turnos_core/serializers.py
✓ apps/turnos_core/views.py
✓ apps/turnos_core/urls.py
✓ apps/turnos_core/services/turnos.py
✓ apps/common/permissions.py
✓ apps/turnos_padel/urls.py (proxy temporal)

✓ apps/auth_core/views.py
✓ apps/auth_core/serializers.py
✓ apps/auth_core/urls.py

✓ apps/pagos_core/views.py
✓ apps/pagos_core/serializers.py
✓ apps/pagos_core/urls.py

✓ apps/clientes_core/views.py
✓ apps/clientes_core/serializers.py
✓ apps/clientes_core/urls.py
```

---

🧠 **Misión cumplida: arquitectura multi-cliente, segura, escalable y lista para nuevos servicios.**
