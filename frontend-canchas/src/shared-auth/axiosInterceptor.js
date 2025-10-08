// shared-auth/axiosInterceptor.js
// Interceptor de Axios para autenticación

import axios from 'axios';
import authService from './authService';

// Crear instancia de axios
const apiClient = axios.create({
  baseURL: window.RUNTIME_CONFIG?.API_BASE_URL || '/api',
  timeout: 10000,
});

// Interceptor de request
apiClient.interceptors.request.use(
  (config) => {
    const token = authService.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor de response
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Si es error 401 y no es un retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Intentar refrescar token
        const newToken = await authService.refreshToken();
        
        // Reintentar request con nuevo token
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Si falla el refresh, redirigir a login
        authService.logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
