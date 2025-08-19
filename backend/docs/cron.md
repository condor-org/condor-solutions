# ⏰ Crons del Sistema de Turnos y Abonos

Este documento detalla los crons automáticos configurados para ejecutarse el **día 1 de cada mes a las 00:00**, dentro del contenedor `cron` del sistema.

---

## 🧩 1. `generar_turnos_mensuales.py`

**Ubicación:**  
`apps/turnos_core/management/commands/generar_turnos_mensuales.py`

**Función principal:**  
Genera todos los turnos del mes **actual** y del **mes siguiente** para todos los prestadores activos.

- **Mes actual** → crea turnos en estado `disponible`.
- **Mes siguiente** → crea turnos en estado `reservado` (bloqueados para renovación de abonos).
- Los turnos del mes siguiente son usados luego por el cron de abonos.

---

## 📆 2. `procesar_abonos_mensuales.py`

**Ubicación:**  
`apps/turnos_padel/management/commands/procesar_abonos_mensuales.py`

**Función principal:**  
Procesa todos los abonos del mes **anterior**.

- Si el abono tiene `renovado = True`:
  - Crea un **nuevo abono** para el mismo usuario.
  - Asigna como `turnos_reservados` los `turnos_prioridad` del abono anterior.
  - Reserva nuevos `turnos_prioridad` para el mes siguiente.
- Si el abono **no fue renovado**:
  - Libera los `turnos_prioridad` para que puedan reservarse normalmente.

---

## 🛠️ Configuración del cron

**Archivo:**  
`backend/docker/crontab`

```cron
0 0 1 * * cd /app && python manage.py generar_turnos_mensuales && python manage.py procesar_abonos_mensuales >> /var/log/cron.log 2>&1
