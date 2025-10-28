// src/api/etheApi.js
// Servicio de API para ETHE Medical System

import axios from 'axios';

// Configuración base de la API
import { API_BASE_URL } from '../config/runtime';
const API_URL = API_BASE_URL;

// Crear instancia de axios
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar token de autenticación
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para manejar errores de respuesta
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expirado o inválido
      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============================================================================
// MÉDICOS
// ============================================================================

export const getMedicos = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    if (filters.establecimiento_id) {
      params.append('establecimiento', filters.establecimiento_id);
    }
    if (filters.categoria) {
      params.append('categoria', filters.categoria);
    }
    if (filters.activo !== undefined) {
      params.append('activo', filters.activo);
    }
    if (filters.con_estadisticas) {
      params.append('con_estadisticas', 'true');
    }
    
    const response = await apiClient.get(`/ethe/medicos/?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching medicos:', error);
    throw error;
  }
};

export const getMedicoById = async (id) => {
  try {
    const response = await apiClient.get(`/ethe/medicos/${id}/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching medico:', error);
    throw error;
  }
};

export const getMedicoEstadisticas = async (id) => {
  try {
    const response = await apiClient.get(`/ethe/medicos/${id}/estadisticas/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching medico estadisticas:', error);
    throw error;
  }
};

// ============================================================================
// PACIENTES
// ============================================================================

export const getPacientes = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    if (filters.medico_id) {
      params.append('medico', filters.medico_id);
    }
    if (filters.categoria) {
      params.append('categoria_actual', filters.categoria);
    }
    if (filters.activo !== undefined) {
      params.append('activo', filters.activo);
    }
    if (filters.search) {
      params.append('search', filters.search);
    }
    if (filters.admin_ministro) {
      // Admin ministro puede ver todos los pacientes
      params.append('all', 'true');
    }
    
    const response = await apiClient.get(`/ethe/pacientes/?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching pacientes:', error);
    throw error;
  }
};

export const getPacienteById = async (id) => {
  try {
    const response = await apiClient.get(`/ethe/pacientes/${id}/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching paciente:', error);
    throw error;
  }
};

export const getPacienteSeguimiento = async (id) => {
  try {
    const response = await apiClient.get(`/ethe/pacientes/${id}/seguimiento-completo/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching paciente seguimiento:', error);
    throw error;
  }
};

export const getPacienteEstadisticasAsistencia = async (id) => {
  try {
    const response = await apiClient.get(`/ethe/pacientes/${id}/estadisticas_asistencia/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching paciente estadisticas:', error);
    throw error;
  }
};

export const getPacienteHistorialCategorias = async (id) => {
  try {
    const response = await apiClient.get(`/ethe/pacientes/${id}/historial_categorias/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching paciente historial:', error);
    throw error;
  }
};

export const ingresarPaciente = async (data) => {
  try {
    const response = await apiClient.post('/ethe/pacientes/ingresar/', data);
    return response.data;
  } catch (error) {
    console.error('Error ingresando paciente:', error);
    throw error;
  }
};

// ============================================================================
// TESTS / RESULTADOS
// ============================================================================

export const getTests = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    if (filters.paciente_id) {
      params.append('paciente', filters.paciente_id);
    }
    if (filters.medico_id) {
      params.append('medico', filters.medico_id);
    }
    if (filters.tipo_test) {
      params.append('tipo_test', filters.tipo_test);
    }
    if (filters.centro_id) {
      params.append('centro', filters.centro_id);
    }
    
    const response = await apiClient.get(`/ethe/tests/?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching tests:', error);
    throw error;
  }
};

export const registrarTest = async (data) => {
  try {
    const response = await apiClient.post('/ethe/tests/', data);
    return response.data;
  } catch (error) {
    console.error('Error registrando test:', error);
    throw error;
  }
};

// ============================================================================
// ESTABLECIMIENTOS
// ============================================================================

export const getEstablecimientos = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    if (filters.activo !== undefined) {
      params.append('activo', filters.activo);
    }
    if (filters.search) {
      params.append('search', filters.search);
    }
    
    const response = await apiClient.get(`/ethe/establecimientos/?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching establecimientos:', error);
    throw error;
  }
};

export const getEstablecimientoById = async (id) => {
  try {
    const response = await apiClient.get(`/ethe/establecimientos/${id}/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching establecimiento:', error);
    throw error;
  }
};

// ============================================================================
// CENTROS DE ATENCIÓN
// ============================================================================

export const getCentros = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    if (filters.establecimiento_id) {
      params.append('establecimiento', filters.establecimiento_id);
    }
    if (filters.categoria) {
      params.append('categorias', filters.categoria);
    }
    if (filters.activo !== undefined) {
      params.append('activo', filters.activo);
    }
    
    const response = await apiClient.get(`/ethe/centros/?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching centros:', error);
    throw error;
  }
};

// ============================================================================
// TURNOS
// ============================================================================

export const getTurnos = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    if (filters.fecha) {
      params.append('fecha', filters.fecha);
    }
    if (filters.estado) {
      params.append('estado', filters.estado);
    }
    if (filters.upcoming) {
      params.append('upcoming', 'true');
    }
    if (filters.prestador_id) {
      params.append('prestador_id', filters.prestador_id);
    }
    
    const response = await apiClient.get(`/turnos/?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching turnos:', error);
    throw error;
  }
};

export const getMiAgenda = async (fecha, scope = 'day') => {
  try {
    const params = new URLSearchParams();
    params.append('scope', scope);
    if (fecha) {
      params.append('date', fecha);
    }
    
    const response = await apiClient.get(`/turnos/agenda/?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching mi agenda:', error);
    throw error;
  }
};

export const marcarAsistencia = async (turnoId, asistio, observaciones = '') => {
  try {
    const response = await apiClient.post(`/turnos/${turnoId}/marcar-asistencia/`, {
      asistio,
      observaciones
    });
    return response.data;
  } catch (error) {
    console.error('Error marcando asistencia:', error);
    throw error;
  }
};

export const reservarTurno = async (data) => {
  try {
    const response = await apiClient.post('/ethe/turnos/reservar/', data);
    return response.data;
  } catch (error) {
    console.error('Error reservando turno:', error);
    throw error;
  }
};

export const cancelarTurnosMasivo = async (data) => {
  try {
    const response = await apiClient.post('/turnos/cancelar-masivo/', data);
    return response.data;
  } catch (error) {
    console.error('Error cancelando turnos:', error);
    throw error;
  }
};

// ============================================================================
// DASHBOARDS / ESTADÍSTICAS
// ============================================================================

export const getDashboardStats = async (role) => {
  try {
    let endpoint = '/ethe/dashboard/estadisticas-generales/';
    
    // Mapear rol a endpoint específico
    switch (role) {
      case 'medico_m1':
        endpoint = '/ethe/dashboard/medico-m1/';
        break;
      case 'medico_m2':
        endpoint = '/ethe/dashboard/medico-m2/';
        break;
      case 'medico_m3':
        endpoint = '/ethe/dashboard/medico-m3/';
        break;
      case 'admin_establecimiento':
        endpoint = '/ethe/dashboard/establecimiento/';
        break;
      case 'admin_ministro':
      case 'admin_ministro_salud':
        endpoint = '/ethe/dashboard/ministro/';
        break;
      default:
        endpoint = '/ethe/dashboard/estadisticas-generales/';
    }
    
    const response = await apiClient.get(endpoint);
    return response.data;
  } catch (error) {
    console.error('Error fetching dashboard stats:', error);
    throw error;
  }
};

// ============================================================================
// DERIVACIÓN
// ============================================================================

export const getCentrosSuperiores = async (centroActualId = 1) => {
  try {
    const response = await apiClient.get(`/ethe/derivacion/centros-superiores/?centro_actual_id=${centroActualId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching centros superiores:', error);
    throw error;
  }
};

export const reservarTurnoDerivacion = async (data) => {
  try {
    const response = await apiClient.post('/ethe/derivacion/reservar-turno/', data);
    return response.data;
  } catch (error) {
    console.error('Error reservando turno derivación:', error);
    throw error;
  }
};

// ============================================================================
// HELPERS
// ============================================================================

export const getApiUrl = (endpoint) => {
  return `${API_URL}${endpoint}`;
};

export default {
  // Médicos
  getMedicos,
  getMedicoById,
  getMedicoEstadisticas,
  
  // Pacientes
  getPacientes,
  getPacienteById,
  getPacienteSeguimiento,
  getPacienteEstadisticasAsistencia,
  getPacienteHistorialCategorias,
  ingresarPaciente,
  
  // Tests
  getTests,
  registrarTest,
  
  // Establecimientos
  getEstablecimientos,
  getEstablecimientoById,
  
  // Centros
  getCentros,
  
  // Turnos
  getTurnos,
  getMiAgenda,
  marcarAsistencia,
  reservarTurno,
  cancelarTurnosMasivo,
  
  // Dashboard
  getDashboardStats,
  
  // Derivación
  getCentrosSuperiores,
  reservarTurnoDerivacion,
  
  // Helpers
  getApiUrl,
};

