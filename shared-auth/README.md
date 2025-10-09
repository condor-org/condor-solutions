# @condor/shared-auth

Módulo compartido de autenticación para todos los frontends de Condor.

## Estructura

```
shared-auth/
├── src/
│   ├── index.js              # Export principal - re-exporta todos los módulos
│   ├── AuthContext.js        # Context de React - define el contexto de autenticación
│   ├── AuthProvider.js       # Provider de React - provee el estado de auth a la app
│   ├── useAuth.js            # Hook personalizado - hook para acceder al contexto de auth
│   ├── authService.js        # Servicio de autenticación - maneja login/logout/refresh
│   ├── oauthClient.js        # Cliente OAuth - maneja el flujo OAuth con Google
│   ├── axiosInterceptor.js   # Interceptor de Axios - añade tokens y maneja refreshes
│   ├── pkce.js              # Utilidades PKCE - funciones para PKCE (code_challenge/verifier)
│   ├── LoginButton.js        # Componente de login - botón de login con Google
│   ├── LogoutButton.js       # Componente de logout - botón de logout
│   └── ProtectedRoute.js     # Componente de ruta protegida - protege rutas que requieren auth
└── package.json
```

## Uso

```javascript
import { AuthProvider, useAuth } from './shared-auth'
```

## Instalación

Este módulo se usa como symlink en cada frontend:

```bash
# En cada frontend
rm -rf src/shared-auth
ln -s ../../shared-auth src/shared-auth
```

