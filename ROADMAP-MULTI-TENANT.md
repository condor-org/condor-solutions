# 🚀 Roadmap Multi-Tenant - Condor

## 📋 Objetivo General
Implementar sistema multi-tenant que permita agregar clientes automáticamente con diferentes tipos de frontend, manteniendo un backend unificado y sistema de autenticación centralizado.

## 🎯 Fases de Implementación

### **Fase 1: Multi-FE Básico (Sin Automatización)**
**Objetivo:** Servir FE diferente según tipo de cliente
**Alcance:** Solo routing, sin automatización

**Componentes:**
- ✅ Modelo Cliente con campo `tipo_fe`
- ✅ Backend API para configuración por hostname
- ✅ Auth compartido entre FEs
- ✅ Nginx routing dinámico con Lua
- ✅ Múltiples containers de FE
- ✅ OAuth compartido (mismo Client ID)

**FEs a Implementar:**
- `frontend-padel` - Profesores Padel (actual)
- `frontend-canchas` - Administración Canchas (nuevo)
- `frontend-medicina` - Medicina (futuro)
- `frontend-superadmin` - SuperAdmin (nuevo)

### **Fase 2: OAuth Compartido**
**Objetivo:** Mismo Client ID para todos los clientes
**Alcance:** Solo OAuth, sin automatización

**Componentes:**
- ✅ Google Console con wildcards
- ✅ Redirect URI dinámico por hostname
- ✅ Configuración centralizada

### **Fase 3: Automatización Básica**
**Objetivo:** Automatizar clientes en DB
**Alcance:** Solo DB, sin DNS/Google

**Componentes:**
- ✅ Scripts de bootstrap automático
- ✅ API para crear clientes
- ✅ Validaciones y verificaciones

### **Fase 4: Usuarios Multi-Tenant**
**Objetivo:** Permitir que usuarios accedan a múltiples clientes
**Alcance:** Sistema de roles y permisos por cliente

**Componentes:**
- 🔄 Modelo UsuarioCliente (usuario + cliente + rol)
- 🔄 Modelo Rol (permisos específicos)
- 🔄 Modelo SesionUsuario (rol activo por sesión)
- 🔄 TenantMiddleware actualizado
- 🔄 OAuth Callback multi-tenant
- 🔄 API para cambiar rol/cliente
- 🔄 Frontend selector de cliente/rol
- 🔄 Seguridad estricta por cliente

**Riesgos:**
- ⚠️ Cambios críticos en autenticación
- ⚠️ Posible ruptura de funcionalidad existente
- ⚠️ Complejidad alta en implementación
- ⚠️ Testing exhaustivo requerido

**Estrategia:**
- 🛡️ Implementación gradual con feature flags
- 🛡️ Mantener lógica actual como fallback
- 🛡️ Testing en dev antes de prod
- 🛡️ Rollback plan definido

### **Fase 5: Automatización Completa**
**Objetivo:** Automatizar DNS y Google Console
**Alcance:** Todo automatizado

**Componentes:**
- ✅ API de DNS (Cloudflare)
- ✅ API de Google Console
- ✅ Frontend SuperAdmin para gestión
- ✅ Workflows automatizados

## 🏗️ Arquitectura General

### **Backend Unificado**
- Mismo backend para todos los clientes
- TenantMiddleware para resolución por hostname
- API centralizada para configuración
- Roles y permisos existentes

### **Frontends Específicos**
- Un FE por tipo de cliente
- Auth compartido entre FEs (módulo shared-auth)
- Assets independientes por FE
- Configuración dinámica por hostname

### **Infraestructura**
- Nginx con routing dinámico
- Docker containers por FE
- OAuth centralizado
- DNS automático (Fase 4)

## 📊 Estado Actual

### **✅ Implementado:**
- Sistema de tenants básico
- OAuth funcional
- Frontend padel operativo
- Backend con roles y permisos

### **🚧 En Desarrollo:**
- Fase 1: Multi-FE básico

### **📋 Pendiente:**
- Fase 2: OAuth compartido
- Fase 3: Automatización básica
- Fase 4: Usuarios Multi-Tenant
- Fase 5: Automatización completa

## 🎯 Criterios de Éxito

### **Fase 1:**
- ✅ Routing dinámico funcional
- ✅ Múltiples FEs operativos
- ✅ Auth compartido entre FEs
- ✅ OAuth compartido funcional
- ✅ Sin cambios manuales por cliente

### **Fase 2:**
- ✅ Mismo Client ID para todos
- ✅ Redirects dinámicos
- ✅ Configuración centralizada

### **Fase 3:**
- ✅ Clientes automáticos en DB
- ✅ Scripts de bootstrap
- ✅ Validaciones automáticas

### **Fase 4:**
- ✅ Usuarios pueden acceder a múltiples clientes
- ✅ Roles específicos por cliente
- ✅ Seguridad estricta por cliente
- ✅ Selector de cliente/rol en frontend
- ✅ Sin acceso no autorizado a datos

### **Fase 5:**
- ✅ DNS automático
- ✅ Google Console automático
- ✅ Frontend SuperAdmin
- ✅ Workflows completos

## 📝 Notas de Implementación

### **Principios:**
- **Mínimos cambios** a infraestructura existente
- **Backward compatibility** con clientes actuales
- **Escalabilidad** para nuevos tipos de cliente
- **Mantenibilidad** del código

### **Restricciones:**
- No romper funcionalidad existente
- Mantener roles y permisos actuales
- Preservar OAuth flow existente
- Minimizar cambios en nginx

## 🔄 Proceso de Actualización

1. **Implementar** cambios de la fase actual
2. **Probar** en entorno de desarrollo
3. **Validar** funcionalidad existente
4. **Documentar** cambios realizados
5. **Actualizar** roadmap con lecciones aprendidas
6. **Avanzar** a la siguiente fase

---

**Última actualización:** 2025-10-08
**Fase actual:** Fase 1 - Multi-FE Básico
**Estado:** En desarrollo
**Próxima fase:** Fase 2 - OAuth Compartido
