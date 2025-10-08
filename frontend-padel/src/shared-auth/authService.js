// shared-auth/authService.js
// Servicio de autenticación compartido

class AuthService {
  constructor() {
    this.baseURL = window.RUNTIME_CONFIG?.API_BASE_URL || '/api';
    this.tokenKey = 'condor_access_token';
    this.refreshTokenKey = 'condor_refresh_token';
  }

  // Obtener token de acceso
  getAccessToken() {
    return localStorage.getItem(this.tokenKey);
  }

  // Obtener refresh token
  getRefreshToken() {
    return localStorage.getItem(this.refreshTokenKey);
  }

  // Guardar tokens
  setTokens(accessToken, refreshToken) {
    localStorage.setItem(this.tokenKey, accessToken);
    if (refreshToken) {
      localStorage.setItem(this.refreshTokenKey, refreshToken);
    }
  }

  // Limpiar tokens
  clearTokens() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshTokenKey);
  }

  // Verificar si está autenticado
  isAuthenticated() {
    const token = this.getAccessToken();
    if (!token) return false;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const now = Date.now() / 1000;
      return payload.exp > now;
    } catch (error) {
      return false;
    }
  }

  // Obtener información del usuario
  getUserInfo() {
    const token = this.getAccessToken();
    if (!token) return null;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return {
        id: payload.user_id,
        email: payload.email,
        name: payload.name,
        picture: payload.picture
      };
    } catch (error) {
      return null;
    }
  }

  // Refrescar token
  async refreshToken() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await fetch(`${this.baseURL}/token/refresh/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh: refreshToken
        })
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      this.setTokens(data.access, data.refresh);
      return data.access;
    } catch (error) {
      this.clearTokens();
      throw error;
    }
  }

  // Logout
  logout() {
    this.clearTokens();
    window.location.href = '/';
  }

  // Obtener headers de autorización
  getAuthHeaders() {
    const token = this.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}

export default new AuthService();
