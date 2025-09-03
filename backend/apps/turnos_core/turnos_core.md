
# turnos_core — Guía rápida (URLs → Views → Serializers → Services/Utils)

> Objetivo: seguir **de punta a punta** cada flujo sin perderse. Concisa, ordenada y enfocada en **calidad de código**, **logs** y **reglas de negocio**.

---

## 0) Conceptos base

- **Modelos clave:** `Turno`, `Prestador`, `Lugar`, `Disponibilidad`, `BloqueoTurnos`, `TurnoBonificado`, `CancelacionAdmin`.
- **Tenancy:** casi todo filtra por `cliente` (directo o vía `Lugar/Prestador`).
- **GFK:** `Turno.recurso` apunta genéricamente (usado con `Prestador`).
- **Estados de Turno:** `disponible | reservado | cancelado`.
- **Bonos:** `TurnoBonificado` (x1/x2/x3/x4), con vigencia, uso y trazabilidad.
- **Eventos/Notifs:** se publican eventos (`turnos.*`, `bonificaciones.*`) y notificaciones in‑app (best‑effort).

---

## 1) Endpoints y flujos (de URL a Service)

### A) Turnos de usuario / prestador

1) `GET /` → **TurnoListView**
   - **Serializer:** `TurnoSerializer`
   - **Qué hace:** lista turnos según rol  
     - `superuser`: todos  
     - `empleado_cliente`: sus turnos como prestador  
     - resto: turnos del usuario  
   - **Filtros:** `estado`, `upcoming` (hoy/ahora en adelante).

2) `POST /reservar/` → **TurnoReservaView**
   - **Serializer:** `TurnoReservaSerializer`
     - `validate`: turno existe y libre; `TipoClasePadel` válido y sede consistente.
     - `create`:
       - Resuelve `tipo_turno` (x1..x4).
       - **Si `usar_bonificado`:** consume primer bono vigente compatible.  
       - **Si NO:** **requiere comprobante** → `ComprobanteService.upload_comprobante(...)` + crea `PagoIntento`.
       - Confirma reserva: setea `usuario`, `estado=reservado`, `tipo_turno`.
   - **Eventos/Notifs:** `turnos.reserva_confirmada` a admins del cliente.

3) `GET /disponibles/?prestador_id=&lugar_id=&fecha=` → **TurnosDisponiblesView**
   - **Serializer salida:** `TurnoSerializer`
   - **Qué hace:** trae turnos `disponible|reservado` futuros (hoy/ahora+), por prestador + sede (y fecha opcional).

4) `POST /cancelar/` → **CancelarTurnoView**
   - **Serializer:** `CancelarTurnoSerializer`
     - Verifica **dueño del turno**, `estado=reservado` y **política**: `utils.cumple_politica_cancelacion` (≥ 6 h).
   - **Transacción:** `select_for_update` del turno.
   - **Flujo:**
     - Libera slot → `usuario=None`, `estado=disponible`.
     - Bonificación:
       - Si **se reservó con bono**:  
         - usuario cancela ⇒ **NO emitir**  
         - admin cancela ⇒ **emitir** (devolución)  
       - Si **NO** se reservó con bono ⇒ emitir si corresponde a política.
     - **Notifs:** si cancela usuario final, notifica admins del cliente.

---

### B) Administración de sedes / prestadores / disponibilidades / bloqueos

5) `router: /sedes/` → **LugarViewSet**
   - **Serializer:** `LugarSerializer`
   - **Permiso:** `SoloAdminEditar` (GET autenticado, mutaciones admin/super).
   - **Al crear:** inyecta `cliente` del admin.

6) `router: /prestadores/` → **PrestadorViewSet**
   - **Serializers:**  
     - list/retrieve → `PrestadorDetailSerializer`  
     - create/update → `PrestadorConUsuarioSerializer`
   - **Queryset:** prestadores activos del **mismo cliente** (filtro opcional por `lugar_id`).  
   - **Acciones:**
     - `DELETE` → elimina `Prestador` y su `User`.
     - `@action GET|POST|DELETE /prestadores/{id}/bloqueos/`
       - GET: lista bloqueos del prestador.
       - POST: crea `BloqueoTurnos` (global o por sede) y devuelve **turnos reservados afectados**.
       - DELETE: elimina bloqueo + **restaura** a `reservado` turnos cancelados por ese bloqueo **que tenían usuario**.
     - `@action POST /prestadores/{id}/forzar_cancelacion_reservados/`
       - Cancela **todos** los turnos `reservado` que caen en el rango del bloqueo y **emite bonos** (si no fue reservado con bono).

7) `router: /disponibilidades/` → **DisponibilidadViewSet**
   - **Serializer:** `DisponibilidadSerializer` (valida duplicados exactos).
   - **Permisos:** super/admin del cliente / empleado (solo las suyas).
   - **Uso:** base para generación de turnos.

8) `router: /bloqueos-turnos/` → **BloqueoTurnosViewSet**
   - CRUD de bloqueos (permiso admin/super). El impacto real se ve en generación (vía `utils.esta_bloqueado`) o en acciones de `PrestadorViewSet`.

---

### C) Generación y cancelaciones administrativas

9) `POST /generar/` → **GenerarTurnosView**
   - **Service:** `services.turnos.generar_turnos_para_prestador(...)`
     - Usa **Disponibilidades** activas y respeta **bloqueos** (`utils.esta_bloqueado`).
     - Idempotente por `bulk_create(..., ignore_conflicts=True)` + `unique_together` en `Turno`.
   - **Salida:** totales y detalle por prestador.

10) `POST /admin/cancelar_por_sede/` → **CancelarPorSedeAdminView**  
    `POST /prestadores/{prestador_id}/cancelar_en_rango/` → **CancelarPorPrestadorAdminView**
   - **Serializers:** `CancelacionPorSedeSerializer` / `CancelacionPorPrestadorSerializer`
     - Validan fechas y horas (`hora_fin > hora_inicio` si ambas vienen).
   - **Service:** `services.cancelaciones_admin.cancelar_turnos_admin(...)`
     - Solo procesa `reservado`.
     - Bonos: **emite** si hay usuario (y compensa si estaba reservado con bono según motivo).
     - Idempotencia con `CancelacionAdmin`.  
     - Publica evento `turnos.cancelacion_admin` y notifica a afectados (warning).
     - **Dry‑run** soportado (no muta BD; devuelve resumen).

---

### D) Bonificaciones (APIs)

11) `GET /bonificados/mios/` y `GET /turnos/bonificados/mios/<tipo_clase_id>/`
   - **View:** `bonificaciones_mias`
   - **Service:** `bonificaciones_vigentes(...)`
   - **Filtro opcional:** por `tipo_clase_id` → x1..x4 (con alias).

12) `POST /bonificaciones/crear-manual/`
   - **View:** `CrearBonificacionManualView`
   - **Serializer:** `CrearTurnoBonificadoSerializer` → `emitir_bonificacion_manual(...)` (solo super/admin).

---

### E) Utilitarios

13) `GET /prestador/mio/` → **prestador_actual**
   - Devuelve `{"id": <prestador_id>}` del `request.user` (o 404).

14) `GET /prestadores_disponibles?lugar_id=`
   - Lista prestadores activos con disponibilidad en una sede.

---

## 2) Serializers (operativo breve)

- **TurnoSerializer:** salida de turnos (enriquece `servicio`, `recurso`, `usuario`, `lugar`, `prestador_nombre`).
- **TurnoReservaSerializer:** valida libre/consistencia; crea reserva + pago/bono.
- **CancelarTurnoSerializer:** dueño + estado + política (≥6 h).
- **DisponibilidadSerializer:** evita duplicados exactos.
- **PrestadorConUsuarioSerializer:** alta/edición prestador + user + disponibilidades.
- **CancelacionPorSede/PrestadorSerializer:** validan rango/horas/dry‑run.
- **BloqueoTurnosSerializer / LugarSerializer / Prestador(Detail)Serializer:** CRUD/lectura.

---

## 3) Services & Utils (quién los usa)

- **`services/turnos.generar_turnos_para_prestador`** → `GenerarTurnosView` + comando mensual.  
- **`services/cancelaciones_admin.cancelar_turnos_admin`** → Cancelaciones admin por sede/prestador.  
- **`services/bonificaciones.*`** → Reserva/cancelación y listados de bonos.  
- **`utils.esta_bloqueado`** → Generación de turnos.  
- **`utils.cumple_politica_cancelacion`** → Validación en cancelación de usuario.

---

## 4) Permisos rápidos

- **Autenticación:** JWT.
- **Roles:**  
  - `super_admin` / `admin_cliente`: mutan sedes, prestadores, disponibilidades, bloqueos, generar/cancelar admin, emitir bonos manuales.  
  - `empleado_cliente`: ve sus turnos y gestiona sus disponibilidades.  
  - Usuario final: reserva/cancela sus turnos y ve sus bonos.

---

## 5) Logging, eventos y resiliencia

- **Logging:** reservas (comprobante/pago), cancelaciones admin (métricas), bonos (emisión/uso), errores.
- **Eventos/Notifs:** `turnos.reserva_confirmada`, `turnos.cancelacion_usuario`, `turnos.cancelacion_admin`, `bonificaciones.*`.
- **Best‑effort:** fallas de notificaciones **no** revierten transacciones.

---

## 6) Job periódico

- **`management/commands/generar_turnos_mensuales.py`**: genera “mes actual + siguiente” en `disponible` (idempotente). Ideal CRON.

---

## 7) Cheatsheet de testing (curl/httpie)

> Reemplazá `$TOKEN` por el JWT.

**Listar mis turnos (desde hoy):**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$API/turnos_core/?upcoming=1"
```

**Buscar slots disponibles de un prestador en una sede:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$API/turnos_core/disponibles/?prestador_id=12&lugar_id=3&fecha=2025-09-05"
```

**Reservar turno con bono (x1/x2/x3/x4 acorde al tipo_clase_id):**
```bash
http POST "$API/turnos_core/reservar/" \
  "Authorization: Bearer $TOKEN" \
  turno_id:=123 tipo_clase_id:=5 usar_bonificado:=true
```

**Reservar turno con comprobante (archivo):**
```bash
curl -H "Authorization: Bearer $TOKEN" -F turno_id=123 -F tipo_clase_id=5 \
     -F archivo=@/path/comprobante.pdf \
     "$API/turnos_core/reservar/"
```

**Cancelar mi turno:**
```bash
http POST "$API/turnos_core/cancelar/" \
  "Authorization: Bearer $TOKEN" \
  turno_id:=123
```

**Generar turnos (admin):**
```bash
http POST "$API/turnos_core/generar/" \
  "Authorization: Bearer $TOKEN" \
  prestador_id:=12 fecha_inicio="2025-09-01" fecha_fin="2025-09-30" duracion_minutos:=60
```

**Cancelación admin por sede (dry‑run):**
```bash
http POST "$API/turnos_core/admin/cancelar_por_sede/" \
  "Authorization: Bearer $TOKEN" \
  sede_id:=3 fecha_inicio="2025-09-01" fecha_fin="2025-09-07" dry_run:=true
```

**Bonificaciones vigentes del usuario:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$API/turnos_core/bonificados/mios/"
```

**Crear bonificación manual (admin):**
```bash
http POST "$API/turnos_core/bonificaciones/crear-manual/" \
  "Authorization: Bearer $TOKEN" \
  usuario_id:=45 tipo_turno="x1" motivo="Corte de luz"
```

---

## 8) Diagramita mental (rápido)

```
URLs → Views/Actions ─────→ Serializers ───→ Services/Utils ───→ Modelos/Efectos
/ (GET)        TurnoListView    → TurnoSerializer  → —                 → Turno (read)
/reservar/     TurnoReservaView → TurnoReservaSer  → Comprobante, Pago → Turno (reserve), Bono opcional
/disponibles/  TurnosDispView   → TurnoSerializer  → —                 → Turno (read)
/cancelar/     CancelarTurno    → CancelarTurnoSer → Bonos, utils      → Turno (free), Bono (si aplica)
/generar/      GenerarTurnos    → —                → generar_turnos... → Turno (create slots)
/admin/...     CancAdmin*       → Cancelacion*Ser  → cancelar_turnos   → Turno (cancel), Bono, Evento
/prestadores   PrestadorViewSet → *Detail/ConUser  → (acciones) bonif  → Prestador+Bloqueos
/disponibil..  DispViewSet      → DispSerializer   → —                 → Disponibilidad
/sedes         LugarViewSet     → LugarSerializer  → —                 → Lugar
/bonificados.. bonificaciones_mias → —            → bonos.vigentes     → TurnoBonificado
/bonif manual  CrearBonifManual → CrearBonifSer    → emitir_manual      → TurnoBonificado
```

---

**Fin.** Mantener esta guía junto al código para onboarding y soporte operativo.
