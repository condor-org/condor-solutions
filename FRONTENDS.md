# Frontends del Sistema Condor

Este documento describe la estructura de los frontends del sistema multi-tenant Condor.

## Estructura de Frontends

### 1. `frontend-padel` (Original)
- **Propósito**: Frontend para profesores de padel
- **Clientes**: lob-padel, distrito-padel, etc.
- **Funcionalidades**: Gestión de turnos, abonos, pagos, notificaciones

### 2. `frontend-canchas` (Nuevo)
- **Propósito**: Frontend para administración de canchas de padel
- **Clientes**: Administradores de canchas
- **Funcionalidades**: Gestión de canchas, horarios, mantenimiento

### 3. `frontend-medicina` (Nuevo)
- **Propósito**: Frontend para empresa de medicina
- **Clientes**: Empresas médicas
- **Funcionalidades**: Gestión de pacientes, citas, historiales

### 4. `frontend-superadmin` (Nuevo)
- **Propósito**: Frontend para super administrador
- **Clientes**: Administradores del sistema
- **Funcionalidades**: Gestión de clientes, configuración, automatización

## Características Comunes

Todos los frontends comparten:

- **Módulo `shared-auth`**: Autenticación OAuth centralizada
- **Misma base de código**: React + Chakra UI
- **Configuración dinámica**: Variables de entorno en runtime
- **Routing dinámico**: Nginx determina qué FE servir

## Configuración

### Variables de Entorno
```bash
PUBLIC_API_BASE_URL=/api
PUBLIC_CLIENTE_ID=1
PUBLIC_NOMBRE_CLIENTE=Cliente
PUBLIC_COLOR_PRIMARIO=#F44336
PUBLIC_COLOR_SECUNDARIO=#000000
PUBLIC_GOOGLE_CLIENT_ID=google_client_id
PUBLIC_OAUTH_REDIRECT_URI=https://hostname/oauth/google/callback
```

### Docker Compose
Cada frontend tiene su propio servicio en `docker-compose-dev.yml`:
- `frontend_padel_dev`
- `frontend_canchas_dev`
- `frontend_medicina_dev`
- `frontend_superadmin_dev`

### Nginx Routing
El Nginx consulta al backend para determinar qué frontend servir basado en el `tipo_fe` del cliente.

## Desarrollo

### Estructura de Archivos
```
frontend-{tipo}/
├── src/
│   ├── shared-auth/          # Módulo de autenticación compartido
│   ├── components/           # Componentes específicos del FE
│   ├── pages/               # Páginas específicas del FE
│   ├── hooks/               # Hooks personalizados
│   └── utils/               # Utilidades
├── docker/                  # Configuración Docker
├── package.json            # Dependencias
└── Dockerfile             # Imagen Docker
```

### Módulo Shared-Auth
Todos los frontends usan el mismo módulo de autenticación:
- `AuthProvider`: Contexto de autenticación
- `useAuth`: Hook para usar la autenticación
- `ProtectedRoute`: Componente para proteger rutas
- `LoginButton`/`LogoutButton`: Botones de autenticación
- `oauthClient`: Cliente OAuth con PKCE
- `axiosInterceptor`: Interceptor para requests HTTP

## Deployment

### Imágenes Docker
Cada frontend genera su propia imagen:
- `ghcr.io/owner/condor-frontend:tag`
- `ghcr.io/owner/condor-frontend-canchas:tag`
- `ghcr.io/owner/condor-frontend-medicina:tag`
- `ghcr.io/owner/condor-frontend-superadmin:tag`

### Pipeline CI/CD
El pipeline debe:
1. Construir cada frontend por separado
2. Generar imagen Docker específica
3. Push a registry
4. Deploy en EC2

## Próximos Pasos

1. **Desarrollar funcionalidades específicas** para cada frontend
2. **Configurar OAuth compartido** en Google Console
3. **Implementar automatización** en frontend-superadmin
4. **Testing** de routing dinámico
5. **Documentación** específica de cada frontend
