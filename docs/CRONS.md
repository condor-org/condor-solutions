# ⏰ Crons del Sistema Condor

Este documento detalla todos los crons automáticos configurados en el sistema, su frecuencia, funcionalidad y logs.

---

## 📅 Resumen de Crons

| Cron | Frecuencia | Hora | Función |
|------|------------|------|---------|
| `generar_turnos_mensuales` | Día 1 de cada mes | 00:00 | Genera turnos del mes actual y siguiente |
| `abonos_diario` | Diario | 00:05 | Procesa recordatorios y transiciones de abonos |
| `limpiar_archivos_comprobantes` | Diario | 02:00 | Limpia archivos de comprobantes antiguos |
| `verificar_memoria` | Diario | 03:00 | Monitorea memoria y disco del sistema |

---

## 🧩 1. `generar_turnos_mensuales.py`

**Ubicación:**  
`apps/turnos_core/management/commands/generar_turnos_mensuales.py`

**Frecuencia:**  
Día 1 de cada mes a las 00:00

**Función principal:**  
Genera todos los turnos del mes **actual** y del **mes siguiente** para todos los prestadores activos.

### ¿Qué hace?

- **Mes actual** → crea turnos en estado `disponible` (desde hoy hasta fin de mes)
- **Mes siguiente** → crea turnos en estado `reservado` (bloqueados para renovación de abonos)
- **Franjas de abono** → marca horarios específicos como `reservado_para_abono=True`
- **Horarios de abono**: 07:00, 08:00, 09:00, 10:00, 11:00, 14:00, 15:00, 16:00, 17:00

### Configuración del cron:
```bash
0 0 1 * * . /etc/environment; /usr/bin/flock -n /tmp/turnos.lock -c 'cd /app && python manage.py generar_turnos_mensuales' >> /proc/1/fd/1 2>&1
```

### Logs:
- Total de turnos generados por prestador
- Franjas de abono marcadas
- Errores de generación

---

## 📆 2. `abonos_diario.py`

**Ubicación:**  
`apps/turnos_padel/management/commands/abonos_diario.py`

**Frecuencia:**  
Todos los días a las 00:05

**Función principal:**  
Procesa recordatorios in-app de abonos y aplica renovaciones o libera prioridades.

### ¿Qué hace?

#### Recordatorios (T-7 y T-1):
- **T-7 días**: Notifica a usuarios sobre abonos próximos a vencer
- **T-1 día**: Recordatorio final antes del vencimiento

#### Transiciones:
- **Renovación automática**: Si `renovado=True`, crea nuevo abono y asigna turnos
- **Liberación**: Si `renovado=False`, libera turnos de prioridad para reserva normal
- **Vencimientos**: Libera abonos vencidos automáticamente

### Configuración del cron:
```bash
5 0 * * * . /etc/environment; /usr/bin/flock -n /tmp/abonos_diario.lock -c 'cd /app && python manage.py abonos_diario' >> /proc/1/fd/1 2>&1
```

### Parámetros opcionales:
```bash
# Solo recordatorios
python manage.py abonos_diario --only recordatorios

# Solo transiciones
python manage.py abonos_diario --only transiciones

# Simular fecha específica
python manage.py abonos_diario --hoy 2024-10-15
```

### Logs:
- Abonos procesados por tipo (recordatorios/transiciones)
- Notificaciones enviadas
- Errores de procesamiento

---

## 🗑️ 3. `limpiar_archivos_comprobantes.py`

**Ubicación:**  
`apps/pagos_core/management/commands/limpiar_archivos_comprobantes.py`

**Frecuencia:**  
Todos los días a las 02:00

**Función principal:**  
Limpia archivos de comprobantes antiguos del sistema de archivos y la base de datos.

### ¿Qué hace?

#### Criterios de limpieza:
- **Retención**: Archivos con `created_at < hoy - 30 días`
- **Tipos**: ComprobantePago y ComprobanteAbono
- **Archivos huérfanos**: Registros en BD sin archivo físico

#### Proceso:
1. **Encuentra** comprobantes antiguos según criterios
2. **Verifica** si el archivo existe en disco
3. **Borra** archivo del sistema de archivos
4. **Elimina** registro de la base de datos
5. **Reporta** estadísticas detalladas

### Configuración del cron:
```bash
0 2 * * * . /etc/environment; /usr/bin/flock -n /tmp/limpiar_comprobantes.lock -c 'cd /app && python manage.py limpiar_archivos_comprobantes --dias 30 --apply' >> /proc/1/fd/1 2>&1
```

### Parámetros opcionales:
```bash
# Modo dry-run (recomendado para probar)
python manage.py limpiar_archivos_comprobantes --dias 30

# Borrado real
python manage.py limpiar_archivos_comprobantes --dias 30 --apply

# Solo comprobantes de pago
python manage.py limpiar_archivos_comprobantes --tipo pagos --dias 30 --apply

# Solo un cliente específico
python manage.py limpiar_archivos_comprobantes --cliente-id 5 --dias 30 --apply

# Diferente retención
python manage.py limpiar_archivos_comprobantes --dias 60 --apply
```

### Logs:
- Comprobantes encontrados por tipo
- Archivos borrados (tamaño en bytes)
- Registros huérfanos eliminados
- Errores de procesamiento
- Resumen final con estadísticas

---

## 📊 4. `verificar_memoria.py`

**Ubicación:**  
`apps/common/management/commands/verificar_memoria.py`

**Frecuencia:**  
Todos los días a las 03:00

**Función principal:**  
Monitorea el uso de memoria, disco y CPU del sistema, alertando si se superan umbrales críticos.

### ¿Qué hace?

#### Métricas monitoreadas:
- **Memoria RAM**: Total, usada, libre, porcentaje
- **Disco**: Total, usado, libre, porcentaje  
- **CPU**: Porcentaje de uso actual

#### Umbrales de alerta:
- **80%+**: Advertencia (amarillo)
- **90%+**: Crítico (rojo)
- **<80%**: OK (verde)

#### Proceso:
1. **Obtiene** métricas del sistema usando `psutil`
2. **Calcula** porcentajes y estados
3. **Evalúa** umbrales de alerta
4. **Registra** logs detallados
5. **Alerta** si es necesario (opcional)

### Configuración del cron:
```bash
0 3 * * * . /etc/environment; /usr/bin/flock -n /tmp/verificar_memoria.lock -c 'cd /app && python manage.py verificar_memoria --umbral 85' >> /proc/1/fd/1 2>&1
```

### Parámetros opcionales:
```bash
# Umbral personalizado (default: 80%)
python manage.py verificar_memoria --umbral 90

# Con alertas habilitadas
python manage.py verificar_memoria --umbral 85 --alertar

# Solo verificar (sin alertas)
python manage.py verificar_memoria --umbral 80
```

### Logs:
- Métricas detalladas de memoria, disco y CPU
- Estados de cada recurso (OK/advertencia/crítico)
- Alertas generadas
- Timestamp de verificación

### Ejemplo de salida:
```
📊 MONITOREO DE RECURSOS - 2024-10-05 03:00:00
💾 MEMORIA:
   Total: 8.0 GB
   Usada: 6.4 GB (80.0%)
   Libre: 1.6 GB
💿 DISCO:
   Total: 20.0 GB
   Usado: 15.2 GB (76.0%)
   Libre: 4.8 GB

⚠️  MEMORIA: 80.0% (umbral: 85%)
```

---

## 🛠️ Configuración Técnica

### Contenedor Cron:
- **Imagen**: `ghcr.io/condor-ai-solutions/condor-cron:${CRON_TAG}`
- **Variables**: Se exportan desde `/etc/environment`
- **Migraciones**: Se aplican automáticamente al iniciar
- **Logs**: Se envían a stdout del contenedor

### Locks:
- **`/tmp/turnos.lock`**: Evita ejecuciones simultáneas de generación de turnos
- **`/tmp/abonos_diario.lock`**: Evita ejecuciones simultáneas de abonos
- **`/tmp/limpiar_comprobantes.lock`**: Evita ejecuciones simultáneas de limpieza
- **`/tmp/verificar_memoria.lock`**: Evita ejecuciones simultáneas de monitoreo

### Zona Horaria:
- **Configurada**: `America/Argentina/Buenos_Aires`
- **Aplicada**: A todos los crons automáticamente

---

## 📊 Flujo Mensual Completo

### Día 1 de cada mes:
1. **00:00** → `generar_turnos_mensuales`
   - Genera turnos del mes actual (disponibles)
   - Genera turnos del mes siguiente (reservados para abonos)
   - Marca franjas horarias de abono

2. **00:05** → `abonos_diario`
   - Procesa abonos del mes anterior
   - Aplica renovaciones o libera prioridades

### Diario:
1. **00:05** → `abonos_diario`
   - Recordatorios T-7 y T-1
   - Transiciones de abonos
   - Liberación de vencidos

2. **02:00** → `limpiar_archivos_comprobantes`
   - Limpia archivos antiguos (>30 días)
   - Elimina registros huérfanos
   - Libera espacio en disco

3. **03:00** → `verificar_memoria`
   - Monitorea uso de memoria y disco
   - Alerta si supera umbrales (80%+)
   - Registra métricas para análisis

---

## 🌐 Endpoint de Monitoreo

**URL:**  
`GET /api/monitoreo/recursos/`

**Autenticación:**  
Solo accesible por `super_admin`

**Función:**  
Endpoint REST para obtener métricas de recursos del sistema en tiempo real.

### Respuesta de ejemplo:
```json
{
  "timestamp": "2024-10-05T03:00:00Z",
  "memoria": {
    "total_gb": 8.0,
    "usada_gb": 6.4,
    "libre_gb": 1.6,
    "porcentaje": 80.0,
    "estado": "advertencia"
  },
  "disco": {
    "total_gb": 20.0,
    "usado_gb": 15.2,
    "libre_gb": 4.8,
    "porcentaje": 76.0,
    "estado": "ok"
  },
  "cpu": {
    "porcentaje": 45.2,
    "estado": "ok"
  },
  "alertas": [
    "Memoria: 80.0% (advertencia)"
  ]
}
```

### Estados:
- **`ok`**: < 80% de uso
- **`advertencia`**: 80-89% de uso  
- **`critico`**: ≥ 90% de uso

### Uso:
```bash
# Obtener métricas actuales
curl -H "Authorization: Bearer <token>" \
     https://padel-dev.cnd-ia.com/api/monitoreo/recursos/
```

---

## 🔍 Monitoreo y Debugging

### Ver logs de crons:
```bash
# Ver logs del contenedor cron
docker logs cron_condor

# Ver logs en tiempo real
docker logs -f cron_condor
```

### Ejecutar crons manualmente:
```bash
# Generar turnos
docker exec -it cron_condor python manage.py generar_turnos_mensuales

# Procesar abonos
docker exec -it cron_condor python manage.py abonos_diario

# Limpiar comprobantes (dry-run)
docker exec -it cron_condor python manage.py limpiar_archivos_comprobantes --dias 30

# Verificar memoria
docker exec -it cron_condor python manage.py verificar_memoria --umbral 85
```

### Verificar locks:
```bash
# Ver locks activos
docker exec -it cron_condor ls -la /tmp/*.lock
```

---

## ⚠️ Consideraciones Importantes

### Seguridad:
- **Modo dry-run**: Por defecto en limpieza de archivos
- **Locks**: Evitan ejecuciones simultáneas
- **Logs detallados**: Cada operación se registra
- **Manejo de errores**: Try/catch en cada operación

### Backup:
- **Archivos**: Se borran permanentemente (sin backup automático)
- **Base de datos**: Los registros se eliminan de la BD
- **Recomendación**: Backup manual antes de cambios importantes

### Retención:
- **Turnos**: Se generan automáticamente cada mes
- **Abonos**: Se procesan según configuración de renovación
- **Comprobantes**: 30 días por defecto (configurable)

### Escalabilidad:
- **Turnos**: Genera ~1000-5000 turnos por mes por prestador
- **Abonos**: Procesa ~100-500 abonos por mes
- **Comprobantes**: Limpia ~50-200 archivos por día

---

## 📝 Mantenimiento

### Actualizar configuración:
1. Modificar `backend/docker/crontab`
2. Rebuild imagen cron: `docker build -f backend/docker/Dockerfile.cron -t condor-cron .`
3. Redeploy contenedor cron

### Ajustar retención:
- Modificar `--dias` en el cron de limpieza
- Probar con `--apply` en modo dry-run primero
- Monitorear logs para verificar funcionamiento

### Troubleshooting:
- **Cron no ejecuta**: Verificar locks, logs, variables de entorno
- **Archivos no se borran**: Verificar permisos, paths, modo dry-run
- **Abonos no procesan**: Verificar estados, fechas, configuración
