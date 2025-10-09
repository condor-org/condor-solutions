// shared-auth/index.js
// Módulo de autenticación compartido para múltiples frontends

export { AuthContext } from './AuthContext.js';
export { AuthProvider } from './AuthProvider.jsx';
export { useAuth } from './useAuth.js';
export { ProtectedRoute } from './ProtectedRoute.jsx';
export { LoginButton } from './LoginButton.jsx';
export { LogoutButton } from './LogoutButton.jsx';
export { authService } from './authService.js';
export { oauthClient } from './oauthClient.js';
export { pkce } from './pkce.js';
export { axiosInterceptor } from './axiosInterceptor.js';
export { default as LoginPage } from './LoginPage.jsx';
export { default as Signup } from './Signup.jsx';
