# turnos_padel — Guía rápida (URLs → Views → Serializers → Services/Utils)

> Objetivo: seguir **de punta a punta** cada flujo sin perderse. Concisa, ordenada y enfocada en **calidad de código**, **logs** y **reglas de negocio**.

---

## 0) Conceptos base

- **Modelos clave:** `ConfiguracionSedePadel`, `TipoClasePadel (x1..x4)`, `TipoAbonoPadel (x1..x4)`, `AbonoMes`.  
- **Core dependencias:** `Lugar`, `Turno` (GFK a `Prestador`), `TurnoBonificado` (en uso indirecto).  
- **Tenancy:** todo cruza por `Lugar.cliente` (admins sólo ven/mutan su cliente; super_admin sin límites).  
- **Abonos:** reservan una **franja fija** (día de semana + hora) por **mes** y crean **prioridad** para el mes siguiente.  
- **Estados de Abono:** `pagado | vencido | cancelado`.  
- **Bloqueos de turnos:** si `Turno.bloqueado_para_reservas=True`, no aparece como candidato.  
- **Notificaciones:** in-app a `admin_cliente` (best-effort; fallar no revierte transacción).  
- **Timezone:** usa `timezone.localdate()` (America/Argentina/Buenos_Aires).

---

## 1) Endpoints y flujos (de URL a Service)

### A) Sedes y configuración

1) `router /sedes/` → **SedePadelViewSet**
   - **Serializer:** `SedePadelSerializer` (incluye `configuracion_padel` embebida).
   - **Qué hace:** CRUD de sedes de pádel.  
     - En `list/retrieve`: **asegura** `ConfiguracionSedePadel` y catálogos default `TipoClasePadel/TipoAbonoPadel` (x1..x4).
     - `perform_create`: inyecta `cliente` desde el usuario.
   - **Permisos:** lectura para usuarios/empleados; mutaciones `admin_cliente`/`super_admin`.  
   - **Logs:** info en create/update; evita N+1 con `select_related/prefetch`.

2) `router /configuracion/{sede_id}/` → **ConfiguracionSedePadelViewSet**
   - **Serializer:** `ConfiguracionSedePadelSerializer` (edición masiva de `tipos_clase` y `tipos_abono` con UPSERT + prune).
   - **Qué hace:** CRUD de la configuración **keyed por `sede_id`** (DX para el front).
   - **Permisos:** igual que sedes; filtra por cliente.  
   - **Errores:** 404 si la sede no tiene configuración.

3) `router /tipos-clase/` → **TipoClasePadelViewSet**
   - **Serializer:** `TipoClasePadelSerializer`
   - **Qué hace:** CRUD de tipos de clase (precios/activo). Filtro opcional `?sede_id=`.
   - **Permisos:** `admin_cliente`/`super_admin` para mutar; lectura resto.

4) `router /tipos-abono/` → **TipoAbonoPadelViewSet**
   - **Serializer:** `TipoAbonoPadelSerializer`
   - **Qué hace:** CRUD de tipos de abono por sede. Filtro opcional `?sede_id=`.
   - **Permisos:** igual que tipos de clase.

---

### B) Abonos mensuales

5) `router /abonos/` → **AbonoMesViewSet**
   - **Serializers:**  
     - `list/retrieve` → `AbonoMesDetailSerializer` (incluye `turnos_reservados` y `turnos_prioridad`).  
     - `create/update` → `AbonoMesSerializer`.
   - **Queryset:**  
     - `super_admin`: todos; `admin_cliente`: por su cliente; `usuario_final`: sólo propios.
   - **Create (POST /abonos/):** *(transaccional)*  
     - Normaliza `usuario` (`usuario`/`usuario_id`) por rol.  
     - Opción `forzar_admin` (omite comprobante si rol lo habilita).  
     - Pasa el control a **`services.abonos.validar_y_confirmar_abono(...)`** con `bonificaciones_ids` y `archivo` si viene.  
     - Al confirmar: **reserva** turnos del mes actual (futuros) y crea **prioridad** del mes siguiente.  
     - **Notifica** in-app a admins del cliente de la sede (best-effort).  
     - **Respuesta:** agrega `resumen` y `monto_sugerido`.
   - **Disponibles (GET /abonos/disponibles/):**  
     - Params requeridos: `sede_id, prestador_id, dia_semana (0..6), anio, mes`. Opcionales: `hora`, `tipo_codigo`.  
     - Devuelve **horas** que están libres en **todas** las fechas del patrón (resto del mes actual + mes siguiente), respetando:  
       `estado == "disponible"` ∧ `!abono_mes_reservado` ∧ `!abono_mes_prioridad` ∧ `!bloqueado_para_reservas`.  
     - Combina horas con catálogo `TipoClasePadel` activo (y `tipo_codigo` si se filtra).
   - **Reservar (POST /abonos/reservar/):** alias DX de `create` con la misma lógica.

---

## 2) Serializers (operativo breve)

- **TipoClasePadelSerializer / TipoAbonoPadelSerializer:** catálogos x1..x4, soportan **UPSERT** mediante `id` o `codigo`.  
- **ConfiguracionSedePadelSerializer:** edita `alias`/`cbu_cvu` y **upsertea** listas `tipos_clase`/`tipos_abono`; hace **prune** de no enviados.  
- **SedePadelSerializer:** crea `Lugar` + `ConfiguracionSedePadel` + catálogos default (x1..x4); `update` delega a `ConfiguracionSedePadelSerializer`.  
- **AbonoMesSerializer (create/update):**  
  - `validate`:  
    - **Unicidad condicional**: si ya hay un `pagado` en la franja (sede+prestador+día+hora+mes), **bloquea**.  
    - **Tenancy**: `usuario`, `prestador` y `tipo_clase.sede` deben pertenecer al **mismo cliente**.  
    - **Consistencia**: `tipo_clase` y (si viene) `tipo_abono` deben corresponder a la sede.  
    - **Existencia/Disponibilidad** de **TODOS** los turnos requeridos:  
      - Mes actual: sólo fechas **>= hoy**.  
      - Mes siguiente: **todas** las fechas del patrón.  
      - Ninguno debe estar `reservado` ni faltar en BD.  
  - `create`: si no viene `monto`, usa `precio` de `tipo_abono` o `tipo_clase`. Loguea contexto.  
  - `to_representation`: añade `monto_sugerido` para UX.
- **AbonoMesDetailSerializer (read):** incluye `TurnoSimpleSerializer` para `turnos_reservados` y `turnos_prioridad`.

---

## 3) Services & Utils (quién los usa)

- **`apps.turnos_padel.services.abonos.validar_y_confirmar_abono(data, bonificaciones_ids, archivo, request, forzar_admin)`**  
  Usado por `AbonoMesViewSet.create/reservar`. Valida reglas (tenancy, unicidad, disponibilidad, pagos/bonos), confirma y arma `resumen`.  
  Publica evento y **no** revierte si fallan notificaciones (best-effort).
- **`apps.turnos_padel.utils.proximo_mes`**  
  Utilidad de fechas en varios puntos.

> Nota: La app depende de **turnos_core** para la existencia y estados de `Turno`, y de **pagos_core** para comprobantes/bonos.

---

## 4) Permisos rápidos

- **Autenticación:** JWT (`JWTAuthentication`).  
- **Roles:**  
  - `super_admin`: sin límites.  
  - `admin_cliente`: ve/muta **sólo** su cliente (valida `Lugar.cliente_id`).  
  - `usuario_final`: sólo sus `AbonoMes`; lectura de catálogos/config; no puede crear abonos para terceros.  
  - `empleado_cliente`: lectura; mutaciones restringidas según endpoint.

---

## 5) Logging, eventos y resiliencia

- **Logs clave:**  
  - `AbonoMesViewSet:get_queryset/create/disponibles/reservar` (id/tipo de usuario, parámetros, resultados).  
  - Validaciones: `unique`, `cliente_mismatch`, `faltantes`, `reservados`.  
  - `create`: falta de `precio` → `monto=0` (warning).  
- **Notificaciones:** `abonos.reserva_confirmada` a `admin_cliente` del **cliente de la sede** con contexto (sede, prestador, día/hora, tipo, montos).  
- **Best-effort:** fallas en notifs **no** invalidan la reserva.

---

## 6) Job periódico (ecosistema abonos)

- **Generación mensual de turnos** (desde `turnos_core`): crea slots **del mes actual y siguiente**.  
- **Procesamiento de abonos** (cron 1° de mes): promueve `turnos_prioridad → turnos_reservados`, reserva nueva prioridad, o libera si no se renovó.  
- **Orden sugerida:** generar turnos **antes** de procesar abonos; durante la ventana, `bloqueado_para_reservas=True`.

---

## 7) Cheatsheet de testing (curl/httpie)

> Reemplazá `$TOKEN` por el JWT. Base path: `$API/padel` (o el que uses para `turnos_padel`).

**Listar sedes con configuración y catálogos embebidos:**
```bash
curl -H "Authorization: Bearer $TOKEN"   "$API/padel/sedes/"
```

**Crear sede + configuración mínima (admin):**
```bash
http POST "$API/padel/sedes/"   "Authorization: Bearer $TOKEN"   nombre="Club Norte" direccion="Av. Siempre 123" referente="Juan" telefono="123456"   configuracion_padel:='{"alias":"club.norte","cbu_cvu":"0000000000000000000000"}'
```

**Editar configuración por `sede_id` (UPSERT + prune de catálogos):**
```bash
http PATCH "$API/padel/configuracion/3/"   "Authorization: Bearer $TOKEN"   alias="club.norte" cbu_cvu="0000003100072077739741"   tipos_clase:='[{"codigo":"x1","precio":7000,"activo":true},{"codigo":"x2","precio":12000,"activo":true}]'   tipos_abono:='[{"codigo":"x1","precio":24000,"activo":true}]'
```

**Consultar horas disponibles para abono (mes actual + siguiente):**
```bash
curl -H "Authorization: Bearer $TOKEN"   "$API/padel/abonos/disponibles/?sede_id=3&prestador_id=8&dia_semana=2&anio=2025&mes=9"
```

**Reservar abono con bonificaciones y comprobante (FormData):**
```bash
curl -H "Authorization: Bearer $TOKEN" -F usuario_id=45 -F sede=3 -F prestador=8      -F anio=2025 -F mes=9 -F dia_semana=2 -F hora=19:00:00      -F tipo_clase=5 -F tipo_abono=5      -F bonificaciones_ids:=\[12,18\]      -F archivo=@/path/comprobante.pdf      "$API/padel/abonos/reservar/"
```

**Reservar abono como usuario final (sin forzar, sin archivo, usa bonos si aplica):**
```bash
http POST "$API/padel/abonos/"   "Authorization: Bearer $TOKEN"   sede:=3 prestador:=8 anio:=2025 mes:=9 dia_semana:=2 hora="19:00:00" tipo_clase:=5
```

**Listar mis abonos (usuario final):**
```bash
curl -H "Authorization: Bearer $TOKEN"   "$API/padel/abonos/"
```

---

## 8) Diagramita mental (rápido)

```
URLs → Views/Actions ─────→ Serializers ───→ Services/Utils ───→ Efectos
/sedes        SedePadelViewSet → SedePadelSer      → —                         → Lugar + Config + catálogos
/configuracion/{sede_id}
              ConfigViewSet     → ConfigSer        → —                         → Alias/CBU + tipos (UPSERT+prune)
/tipos-clase  TiposClaseViewSet → TipoClaseSer     → —                         → Catálogo clase (precio/activo)
/tipos-abono  TiposAbonoViewSet → TipoAbonoSer     → —                         → Catálogo abono (precio/activo)
/abonos       AbonoMesViewSet   → AbonoMesSer*     → services.abonos.validar_y_confirmar_abono
                                                                             → Reserva + Prioridad + Notifs
/abonos/disponibles
              (action GET)      → —                → utils fechas + reglas     → Horas válidas (todas las fechas)
/abonos/reservar
              (action POST)     → AbonoMesSer*     → same service              → Igual a create (DX front)
```

---

**Fin.** Guardá este `.md` junto al módulo para onboarding y soporte operativo.
