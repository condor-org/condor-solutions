# Shared Auth Module

Módulo de autenticación compartido para múltiples frontends en el sistema Condor.

## Características

- **OAuth 2.0 con PKCE**: Autenticación segura con Google
- **JWT Token Management**: Manejo automático de tokens de acceso y refresh
- **Axios Interceptor**: Interceptores automáticos para requests HTTP
- **React Context**: Contexto de autenticación para React
- **Protected Routes**: Componentes para proteger rutas
- **Reutilizable**: Mismo código para todos los frontends

## Uso

### 1. Configurar el Provider

```jsx
import { AuthProvider } from './shared-auth';

function App() {
  return (
    <AuthProvider>
      {/* Tu aplicación */}
    </AuthProvider>
  );
}
```

### 2. Usar el Hook

```jsx
import { useAuth } from './shared-auth';

function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuth();
  
  if (!isAuthenticated) {
    return <div>No autenticado</div>;
  }
  
  return <div>Hola {user.name}</div>;
}
```

### 3. Proteger Rutas

```jsx
import { ProtectedRoute } from './shared-auth';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      } />
    </Routes>
  );
}
```

### 4. Botones de Login/Logout

```jsx
import { LoginButton, LogoutButton } from './shared-auth';

function Header() {
  return (
    <div>
      <LoginButton>Iniciar Sesión</LoginButton>
      <LogoutButton>Cerrar Sesión</LogoutButton>
    </div>
  );
}
```

### 5. Requests HTTP

```jsx
import apiClient from './shared-auth/axiosInterceptor';

// Los headers de autorización se agregan automáticamente
const response = await apiClient.get('/api/user/profile/');
```

## Configuración

El módulo usa las siguientes variables de entorno:

- `GOOGLE_CLIENT_ID`: ID del cliente OAuth de Google
- `OAUTH_REDIRECT_URI`: URI de redirección para OAuth
- `API_BASE_URL`: URL base de la API

## Estructura

```
shared-auth/
├── index.js              # Exportaciones principales
├── AuthContext.js        # Contexto de React
├── AuthProvider.js       # Proveedor del contexto
├── useAuth.js           # Hook personalizado
├── ProtectedRoute.js    # Componente para proteger rutas
├── LoginButton.js       # Botón de login
├── LogoutButton.js      # Botón de logout
├── authService.js       # Servicio de autenticación
├── oauthClient.js       # Cliente OAuth
├── axiosInterceptor.js  # Interceptor de Axios
├── pkce.js             # Utilidades PKCE
└── README.md           # Documentación
```

## Dependencias

- React 18+
- Axios
- Chakra UI (para componentes)
- React Router (para ProtectedRoute)
