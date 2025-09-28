# Debug Session - 26 de Septiembre 2024

## Problema Principal
El modal de pago para renovación de abonos muestra **"$0"** en el "Valor restante" y "MONTO", indicando que el cálculo dinámico de precios no está funcionando correctamente.

## Cambios Implementados Hoy

### 1. Corrección en `calcularTurnosDelMes`
**Archivo**: `frontend-padel/src/pages/user/ReservarAbono.jsx`
**Línea**: 266
**Problema**: `new Date(anio, mes, 0)` estaba mal
**Solución**: Cambiado a `new Date(anio, mes - 1, 0).getDate()`

```javascript
// ANTES (INCORRECTO)
const diasEnMes = new Date(anio, mes, 0).getDate();

// DESPUÉS (CORREGIDO)
const diasEnMes = new Date(anio, mes - 1, 0).getDate();
```

### 2. Logs de Debug Agregados
**Archivo**: `frontend-padel/src/pages/user/ReservarAbono.jsx`
**Función**: `abrirRenovarAbono`
**Líneas**: 461, 471, 487, 493, 495

Se agregaron `console.log` para debuggear:
- Parámetros de renovación (año, mes, día de la semana, turnos del mes)
- Configuración de abonos personalizados
- Precios calculados
- Errores en el proceso

### 3. Dependencia Faltante Instalada
**Archivo**: `frontend-padel/package.json`
**Dependencia**: `@chakra-ui/theme-tools`
**Estado**: ✅ Instalada y funcionando

## Estado Actual
- ✅ Build exitoso sin errores
- ✅ Aplicación funcionando (código 200)
- ✅ JavaScript compilado en el contenedor
- ❌ **PROBLEMA**: Los cambios no se reflejan en la aplicación

## Posibles Causas del Problema

### 1. Cache del Navegador
- El navegador puede estar usando una versión cacheada del JavaScript
- **Solución**: Hard refresh (Ctrl+F5 o Cmd+Shift+R)

### 2. Contenedor Docker
- El contenedor puede estar usando una imagen antigua
- **Verificación**: `docker images` para ver las imágenes disponibles
- **Solución**: Rebuild completo con `--no-cache`

### 3. Archivos No Sincronizados
- Los cambios pueden no haberse copiado correctamente al contenedor
- **Verificación**: `docker exec condor_frontend_1 ls -la /usr/share/nginx/html/static/js/`

## Pasos para Verificar Mañana

### 1. Verificar que los cambios estén en el contenedor
```bash
# Verificar archivos JavaScript en el contenedor
docker exec condor_frontend_1 ls -la /usr/share/nginx/html/static/js/

# Buscar logs de debug en el navegador
# Abrir DevTools -> Console y buscar "DEBUG renovación"
```

### 2. Verificar logs de debug
- Abrir la aplicación en el navegador
- Ir a la sección de abonos
- Intentar renovar un abono
- Revisar la consola del navegador para ver los logs de debug

### 3. Verificar cálculo de turnos
Los logs deberían mostrar:
```javascript
DEBUG renovación normal: { anio: 2025, mes: 10, diaSemana: 0, turnosDelMesSiguiente: 4, precioUnit: 1500 }
DEBUG precio final: { precioAbono: 6000, precioUnit: 1500, tipoClase: {...}, configuracionPersonalizada: null }
```

### 4. Si los logs no aparecen
- Verificar que el archivo JavaScript esté actualizado
- Hacer rebuild completo: `docker compose -f docker-compose-local.yml build --no-cache frontend`
- Reiniciar contenedores: `docker compose -f docker-compose-local.yml down && docker compose -f docker-compose-local.yml up -d`

## Archivos Modificados Hoy

1. `frontend-padel/src/pages/user/ReservarAbono.jsx`
   - Línea 266: Corrección en `calcularTurnosDelMes`
   - Líneas 461, 471, 487, 493, 495: Logs de debug en `abrirRenovarAbono`

2. `frontend-padel/package.json`
   - Agregada dependencia `@chakra-ui/theme-tools`

## Comandos Utilizados

```bash
# Build del frontend
docker compose -f docker-compose-local.yml build frontend

# Levantar aplicación
docker compose -f docker-compose-local.yml up -d

# Verificar estado
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
```

## Próximos Pasos

1. **Verificar logs de debug** en el navegador
2. **Confirmar que los cambios estén en el contenedor**
3. **Si persiste el problema**: Rebuild completo con `--no-cache`
4. **Limpiar cache del navegador** si es necesario
5. **Verificar que la función `calcularTurnosDelMes` esté calculando correctamente**

## Notas Importantes

- Los logs de debug están temporalmente en el código para diagnosticar el problema
- Una vez solucionado, se deben remover los `console.log`
- El problema principal parece estar en el cálculo de turnos del mes
- La función `calcularTurnosDelMes` es crítica para el cálculo de precios dinámicos
