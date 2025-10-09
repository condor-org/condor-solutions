// shared-auth/index.js
// Módulo de autenticación compartido para múltiples frontends

export { default as AuthContext } from './AuthContext';
export { default as AuthProvider } from './AuthProvider';
export { default as useAuth } from './useAuth';
export { default as ProtectedRoute } from './ProtectedRoute';
export { default as LoginButton } from './LoginButton';
export { default as LogoutButton } from './LogoutButton';
export { default as authService } from './authService';
export { default as oauthClient } from './oauthClient';
export { default as pkce } from './pkce';
export { default as axiosInterceptor } from './axiosInterceptor';
export { default as LoginPage } from './LoginPage';
export { default as Signup } from './Signup';
