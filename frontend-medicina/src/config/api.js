// Configuración de la API
import { API_BASE_URL } from './runtime';

export const API_ENDPOINTS = {
  // Autenticación
  LOGIN: `${API_BASE_URL}/auth/login/`,
  LOGOUT: `${API_BASE_URL}/auth/logout/`,
  REFRESH: `${API_BASE_URL}/auth/refresh/`,
  FORGOT_PASSWORD: `${API_BASE_URL}/auth/forgot-password/`,
  RESET_PASSWORD: `${API_BASE_URL}/auth/reset-password/`,
  
  // ETHE - Pacientes
  PACIENTES: `${API_BASE_URL}/ethe/pacientes/`,
  PACIENTE_PERFIL: `${API_BASE_URL}/ethe/pacientes/mi-perfil/`,
  PACIENTE_INGRESAR: `${API_BASE_URL}/ethe/pacientes/ingresar/`,
  PACIENTE_ESTADISTICAS: `${API_BASE_URL}/ethe/pacientes/mi-perfil/estadisticas-asistencia/`,
  PACIENTE_HISTORIAL: `${API_BASE_URL}/ethe/pacientes/mi-perfil/historial-categorias/`,
  
  // ETHE - Médicos
  MEDICOS: `${API_BASE_URL}/ethe/medicos/`,
  MEDICO_PERFIL: `${API_BASE_URL}/ethe/medicos/mi-perfil/`,
  
  // ETHE - Tests
  TESTS: `${API_BASE_URL}/ethe/tests/`,
  TESTS_MIS: `${API_BASE_URL}/ethe/tests/mis-tests/`,
  
  // ETHE - Centros
  CENTROS: `${API_BASE_URL}/ethe/centros/`,
  
  // ETHE - Establecimientos
  ESTABLECIMIENTOS: `${API_BASE_URL}/ethe/establecimientos/`,
  
  // ETHE - Dashboard
  DASHBOARD_ESTADISTICAS: `${API_BASE_URL}/ethe/dashboard/estadisticas-generales/`,
  
  // Turnos
  TURNOS: `${API_BASE_URL}/turnos/`,
  TURNOS_MIS: `${API_BASE_URL}/turnos/mis-turnos/`,
  TURNOS_DISPONIBLES: `${API_BASE_URL}/turnos/disponibles/`,
  TURNOS_PROXIMO: `${API_BASE_URL}/turnos/proximo/`,
  TURNOS_RESERVAR: `${API_BASE_URL}/ethe/turnos/reservar/`,
  TURNOS_MARCAR_ASISTENCIA: `${API_BASE_URL}/turnos/{id}/marcar-asistencia/`,
  TURNOS_CANCELAR_MASIVO: `${API_BASE_URL}/turnos/cancelar-masivo/`,
};

export const getApiUrl = (endpoint, params = {}) => {
  let url = endpoint;
  
  // Reemplazar parámetros en la URL
  Object.keys(params).forEach(key => {
    url = url.replace(`{${key}}`, params[key]);
  });
  
  return url;
};

export default API_ENDPOINTS;
