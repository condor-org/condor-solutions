# 📋 Endpoints para Gestión de Usuarios - Admin

Este documento describe los nuevos endpoints implementados para mejorar la experiencia del admin en la gestión de usuarios.

---

## 🎯 Endpoints Implementados

### **1. Eliminar Bonificación**
```http
DELETE /api/turnos/bonificaciones/{bonificacion_id}/
```

**Descripción:** Elimina una bonificación específica del sistema.

**Permisos:** Solo `super_admin` y `admin_cliente`

**Parámetros:**
- `bonificacion_id` (path): ID de la bonificación a eliminar

**Body (opcional):**
```json
{
  "motivo": "Eliminada por administrador"
}
```

**Respuesta exitosa (200):**
```json
{
  "ok": true,
  "message": "Bonificación eliminada correctamente"
}
```

**Errores:**
- `403`: No autorizado
- `404`: Bonificación no encontrada
- `500`: Error interno

---

### **2. Obtener Bonificaciones de Usuario**
```http
GET /api/turnos/bonificados/usuario/{usuario_id}/
```

**Descripción:** Obtiene todas las bonificaciones de un usuario específico.

**Permisos:** Solo `super_admin` y `admin_cliente`

**Parámetros:**
- `usuario_id` (path): ID del usuario
- `tipo_clase_id` (query, opcional): Filtrar por tipo de clase

**Respuesta exitosa (200):**
```json
[
  {
    "id": 123,
    "motivo": "Corte de luz",
    "tipo_turno": "x1",
    "fecha_creacion": "2024-10-05T10:30:00Z",
    "valido_hasta": "2024-11-05",
    "valor": 5000.00,
    "usado": false
  }
]
```

**Errores:**
- `403`: No autorizado
- `404`: Usuario no encontrado
- `500`: Error interno

---

### **3. Obtener Turnos de Usuario**
```http
GET /api/turnos/usuario/{usuario_id}/
```

**Descripción:** Obtiene todos los turnos de un usuario específico.

**Permisos:** Solo `super_admin` y `admin_cliente`

**Parámetros:**
- `usuario_id` (path): ID del usuario
- `estado` (query, opcional): Filtrar por estado (`disponible`, `reservado`, `cancelado`)
- `upcoming` (query, opcional): Solo turnos futuros (`true`/`false`)
- `solo_sueltos` (query, opcional): Solo turnos sueltos, no de abonos (`true`/`false`)

**Respuesta exitosa (200):**
```json
[
  {
    "id": 456,
    "fecha": "2024-10-10",
    "hora": "19:00:00",
    "lugar": {
      "id": 3,
      "nombre": "Sede Centro"
    },
    "tipo_turno": "x1",
    "estado": "reservado",
    "usuario": {
      "id": 45,
      "nombre": "Juan",
      "apellido": "Pérez"
    }
  }
]
```

**Errores:**
- `403`: No autorizado
- `404`: Usuario no encontrado
- `500`: Error interno

---

## 🔐 Seguridad y Permisos

### **Control de Acceso:**
- **`super_admin`**: Acceso completo a todos los usuarios
- **`admin_cliente`**: Solo usuarios de su mismo cliente
- **Otros roles**: Acceso denegado

### **Validaciones:**
- Verificación de existencia del usuario
- Verificación de permisos por cliente
- Logging de todas las operaciones
- Manejo de errores con mensajes descriptivos

---

## 📝 Ejemplos de Uso

### **Eliminar Bonificación:**
```bash
curl -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"motivo": "Bonificación duplicada"}' \
  "https://api.condor.com/api/turnos/bonificaciones/123/"
```

### **Obtener Bonificaciones de Usuario:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.condor.com/api/turnos/bonificados/usuario/45/"
```

### **Obtener Turnos Sueltos de Usuario:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.condor.com/api/turnos/usuario/45/?solo_sueltos=true&upcoming=true"
```

---

## 🚀 Integración Frontend

### **Componentes React:**
```jsx
// Eliminar bonificación
const eliminarBonificacion = async (bonificacionId, motivo) => {
  const response = await axiosAuth(accessToken, logout).delete(
    `/turnos/bonificaciones/${bonificacionId}/`,
    { motivo }
  );
  return response.data;
};

// Obtener bonificaciones de usuario
const obtenerBonificacionesUsuario = async (usuarioId) => {
  const response = await axiosAuth(accessToken, logout).get(
    `/turnos/bonificados/usuario/${usuarioId}/`
  );
  return response.data;
};

// Obtener turnos de usuario
const obtenerTurnosUsuario = async (usuarioId, filtros = {}) => {
  const params = new URLSearchParams(filtros);
  const response = await axiosAuth(accessToken, logout).get(
    `/turnos/usuario/${usuarioId}/?${params}`
  );
  return response.data;
};
```

---

## 📊 Logging y Monitoreo

### **Logs Generados:**
- `[eliminar_bonificacion]`: Eliminación de bonificaciones
- `[bonificaciones_usuario]`: Consulta de bonificaciones por usuario
- `[turnos_usuario]`: Consulta de turnos por usuario

### **Métricas:**
- Número de bonificaciones eliminadas
- Consultas de usuarios por admin
- Errores de permisos

---

## ⚠️ Consideraciones Importantes

### **Performance:**
- Los endpoints incluyen `select_related` para optimizar consultas
- Filtros opcionales para reducir datos transferidos
- Logging mínimo para no impactar performance

### **Auditoría:**
- Todas las operaciones se registran en logs
- Motivos de eliminación se almacenan
- Trazabilidad completa de cambios

### **Escalabilidad:**
- Endpoints diseñados para manejar múltiples usuarios
- Filtros eficientes para grandes volúmenes
- Paginación disponible en endpoints de listado

---

**Fin del documento.**
