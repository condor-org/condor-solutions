
# pagos_core — Guía rápida (URLs → Views → Serializers → Services/Utils)

> Objetivo: seguir **de punta a punta** cada flujo sin perderse. Concisa, ordenada y enfocada en **calidad de código**, **logs** y **reglas de negocio**.  
> **Nota:** El modelo `ConfiguracionPago` fue eliminado. No debe referenciarse en ningún lado.

---

## 0) Conceptos base

- **Modelos clave:** `ComprobantePago` (turnos), `ComprobanteAbono` (abonos mensuales), `PagoIntento` (trazabilidad de aprobación).  
- **Dependencias:** `Turno` (turnos_core), `AbonoMes` (turnos_padel).  
- **Estados relevantes:**
  - `PagoIntento.estado`: `pre_aprobado | confirmado | rechazado`.
  - `ComprobantePago/ComprobanteAbono.valido`: `True/False` (set por backoffice).
  - `Turno.estado`: `disponible | reservado | cancelado`.
  - `AbonoMes.estado`: `pagado | pendiente_validacion | cancelado`.
- **Archivos:** soporta `pdf/png/jpg/jpeg/webp/bmp` hasta 3 MB.
- **Tenancy:** alcance por cliente a través de `Turno.lugar.cliente` / `AbonoMes.sede.cliente`.
- **Best‑effort:** fallas de notificaciones externas **no** revierten transacciones (si aplica en services).

---

## 1) Endpoints y flujos (de URL a View)

1) `GET|POST /pagos/comprobantes/` → **ComprobanteView**
   - **Serializers:** `GET` → `ComprobantePagoSerializer`, `POST` → `ComprobanteUploadSerializer`.
   - **Qué hace:**
     - `GET`: lista comprobantes del alcance del usuario (scope por rol).
       - Filtro especial `?solo_preaprobados=1` → anota `PagoIntento(pre_aprobado)` asociado.
     - `POST`: sube archivo, valida (tamaño/extensión/permiso), delega a **`ComprobanteService.upload_comprobante`**, retorna datos OCR y metadatos.

2) `GET /pagos/comprobantes/{pk}/descargar/` → **ComprobanteDownloadView**
   - **Qué hace:** valida acceso vía **`ComprobanteService.download_comprobante`** y devuelve el binario (`FileResponse`).

3) `PATCH /pagos/comprobantes/{pk}/aprobar|rechazar/` → **ComprobanteAprobarRechazarView**
   - **Qué hace:** para `ComprobantePago` o `ComprobanteAbono`:
     - **aprobar**: marca `valido=True`, confirma `PagoIntento`, y (si abono) pone `AbonoMes.estado=pagado`.
     - **rechazar**: marca `valido=False`, pone `PagoIntento=rechazado` y **libera recursos**:
       - Turno: vuelve a `disponible` y quita `usuario/tipo_turno` si corresponde.
       - Abono: limpia `turnos_reservados`/`turnos_prioridad`, estado `cancelado`.

4) `GET /pagos/pendientes/` → **PagosPendientesCountView**
   - **Qué hace:** métrica para admins del cliente (`valido=False` de `ComprobantePago`).

5) `POST /pagos/comprobantes-abono/` → **ComprobanteAbonoView**
   - **Qué hace:** confirma un `AbonoMes` aplicando bonificaciones y exigiendo comprobante si `neto>0`.
   - **Flujo resumido:**
     - Calcula `neto = precio_abono - (cantidad_bonos * precio_clase)`.
     - Si `neto>0` → `archivo` obligatorio.
     - Marca `AbonoMes.estado`: `pagado` si `neto==0` o `pendiente_validacion` si hay archivo.
     - Aplica bonos a `turnos_reservados` en orden cronológico.
     - Limpieza: si falla y el abono quedó vacío, se borra (housekeeping).

---

## 2) Serializers (operativo breve)

- **ComprobanteUploadSerializer (POST /comprobantes/):**
  - Valida `turno` existente y alcance por rol (`usuario_final` dueño del turno, `admin_cliente` dentro del cliente).
  - Valida archivo (≤3 MB, extensión permitida).
  - `create` delega a `ComprobanteService.upload_comprobante(...)`.

- **ComprobantePagoSerializer (GET /comprobantes/):**
  - Denormaliza campos de `Turno` (usuario, profesor, sede, cliente) para listados.
  - **Sugerencia futura:** reemplazar `print()` por `logger` en getters.

- **TurnoReservaSerializer (flujo interno de reserva de turno):**
  - `usuario_final` → requiere comprobante; `admin_cliente` → puede reservar sin comprobante.
  - Asegura turno libre y pertenencia al cliente.

- **ComprobanteAbonoUploadSerializer (POST /comprobantes-abono/):**
  - Valida `AbonoMes` del mismo cliente del usuario.
  - `create` delega a `ComprobanteService.upload_comprobante_abono(...)` (maneja bonificaciones y archivo).

---

## 3) Views (puntos clave)

- **ComprobanteView**
  - Autenticación JWT, permisos `IsAuthenticated`.
  - Filtros: `ComprobantePagoFilter` + `OrderingFilter` (`created_at`, `valido`).
  - Query param `solo_preaprobados` usa `Exists( PagoIntento(pre_aprobado) )` con `ContentType`.

- **ComprobanteDownloadView**
  - Usa `ComprobanteService` para validar ownership/alcance antes de abrir el binario.

- **ComprobanteAprobarRechazarView**
  - Permisos: `EsAdminDeSuCliente | EsSuperAdmin`.
  - `@transaction.atomic` y tratamiento separado para `ComprobantePago` y `ComprobanteAbono`.
  - Reglas de **liberación** coherentes (turnos y abonos).

- **PagosPendientesCountView**
  - Conteo por cliente del request (solo admins/super).

- **ComprobanteAbonoView**
  - Calcula precios (`tipo_abono` o `tipo_clase`) y **bonificaciones** por alias (`x1..x4` y nombres históricos).
  - Aplica bonos a `turnos_reservados` y setea `estado` acorde a `neto`.
  - Housekeeping: borrado del abono si quedó vacío tras error.

---

## 4) Services & Utils (quién los usa)

- **`services.comprobantes.upload_comprobante(turno_id, file_obj, usuario)`**
  - OCR/parsing + validaciones (tamaño, extensión ya vienen del serializer).
  - Crea `ComprobantePago` + `PagoIntento(pre_aprobado)` y retorna el comprobante.
  - Debe validar alcance del usuario al turno (seguridad de tenant).

- **`services.comprobantes.download_comprobante(comprobante_id, usuario)`**
  - Verifica permisos y existencia del archivo en storage. Retorna la instancia para `FileResponse`.

- **`services.comprobantes.upload_comprobante_abono(abono_mes_id, file_obj, usuario, cliente, bonificaciones_ids)`**
  - Aplica/valida bonificaciones y archivo si `neto>0`.
  - Setea `AbonoMes.estado` (`pagado`/`pendiente_validacion`) y devuelve datos.

> Si existen eventos/notificaciones, mantener **best‑effort** (no romper transacción de pagos si falla el canal).

---

## 5) Permisos rápidos

- **Autenticación:** JWT (`JWTAuthentication`).  
- **Roles:**  
  - `super_admin`: sin límites.  
  - `admin_cliente`: ve y opera solo en su cliente.  
  - `usuario_final`: puede subir comprobantes de **sus** turnos y confirmar **sus** abonos.  
  - `empleado_cliente`: normalmente restringido (según scopes de views específicas).

---

## 6) Logging y resiliencia

- **Logs recomendados:**
  - Upload/Download: `user_id`, `turno_id/comprobante_id`, nombre de archivo, tamaño, resultado.  
  - Aprobar/Rechazar: `comprobante_id`, tipo (pago/abono), cambios de estado de `PagoIntento`, `Turno/AbonoMes`.  
  - Abonos: cálculo de `neto`, `bonos_aplicados`, `estado_final`.
- **Errores de storage/OCR:** log `error/exception` con contexto y no exponer paths internos en respuesta.
- **Transacciones:** usar `@transaction.atomic` donde se tocan múltiples modelos (p. ej., rechazo de abono).

---

## 7) Cheatsheet de testing (curl/httpie)

> Reemplazá `$TOKEN` por el JWT. Base path: `$API/pagos` (ajustar a tu router real).

**Listar comprobantes (últimos primero):**
```bash
curl -H "Authorization: Bearer $TOKEN"   "$API/pagos/comprobantes/?ordering=-created_at"
```

**Listar solo con preaprobados:**
```bash
curl -H "Authorization: Bearer $TOKEN"   "$API/pagos/comprobantes/?solo_preaprobados=1"
```

**Subir comprobante de un turno:**
```bash
curl -H "Authorization: Bearer $TOKEN"      -F turno_id=123 -F archivo=@/path/comprobante.pdf      "$API/pagos/comprobantes/"
```

**Descargar comprobante:**
```bash
curl -H "Authorization: Bearer $TOKEN" -L   "$API/pagos/comprobantes/45/descargar/" -o comprobante_45.pdf
```

**Aprobar comprobante:**
```bash
http PATCH "$API/pagos/comprobantes/45/aprobar/" "Authorization: Bearer $TOKEN"
```

**Rechazar comprobante:**
```bash
http PATCH "$API/pagos/comprobantes/45/rechazar/" "Authorization: Bearer $TOKEN"
```

**Confirmar abono con bonos y archivo (FormData):**
```bash
curl -H "Authorization: Bearer $TOKEN"      -F abono_mes_id=77      -F bonificaciones_ids:=\[12,18\]      -F archivo=@/path/comprobante.pdf      "$API/pagos/comprobantes-abono/"
```

---

## 8) Diagramita mental

```
URLs → Views ───────────→ Serializers ─────────→ Services ─────────→ Efectos
/comprobantes   ComprobanteView  → Upload/Read       → upload_comprobante    → ComprobantePago + PagoIntento
/descargar      DownloadView     → —                 → download_comprobante  → FileResponse
/{id}/aprobar|rechazar
                AprobarRechazar  → —                 → —                     → PagoIntento + Turno/AbonoMes
/pendientes     PendientesCount  → —                 → —                     → Métrica por cliente
/comprobantes-abono
                ComprobAbonoView → AbonoUpload       → upload_comprob_abono  → AbonoMes (bonos + estado)
```

---

**Fin.** Guardá este `.md` junto al módulo para onboarding y auditorías de backoffice.
