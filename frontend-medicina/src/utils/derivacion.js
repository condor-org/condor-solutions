// src/utils/derivacion.js
// Utilidades para lógica de derivación de pacientes

/**
 * Determina si un paciente necesita ser derivado a una categoría superior
 * @param {Object} paciente - Objeto paciente con su información
 * @param {string} categoriaMedico - Categoría del médico actual (C1, C2, C3)
 * @returns {Object} - { necesitaDerivacion: boolean, categoriaDestino: string, motivo: string }
 */
export const necesitaDerivacion = (paciente, categoriaMedico) => {
  // Lógica para determinar si un paciente necesita derivación
  // Basado en la categoría del médico y la categoría actual del paciente
  
  const categoriaActual = paciente.categoria_actual;
  
  // M1 (C1) puede derivar a C2
  if (categoriaMedico === 'C1' && categoriaActual === 'C1') {
    // Verificar si tiene resultados que justifiquen derivación a C2
    if (paciente.ultimo_test && paciente.ultimo_test.tipo === 'POCUS') {
      if (paciente.ultimo_test.resultado === 'ALTO' || paciente.ultimo_test.resultado === 'CRITICO') {
        return {
          necesitaDerivacion: true,
          categoriaDestino: 'C2',
          motivo: 'Resultados de POCUS indican necesidad de evaluación C2'
        };
      }
    }
    
    // Verificar si tiene FIB4 alto
    if (paciente.ultimo_test && paciente.ultimo_test.tipo === 'FIB4') {
      if (paciente.ultimo_test.resultado === 'ALTO') {
        return {
          necesitaDerivacion: true,
          categoriaDestino: 'C2',
          motivo: 'FIB4 alto indica necesidad de evaluación C2'
        };
      }
    }
  }
  
  // M2 (C2) puede derivar a C3
  if (categoriaMedico === 'C2' && categoriaActual === 'C2') {
    // Verificar si tiene FIBROSCAN alto
    if (paciente.ultimo_test && paciente.ultimo_test.tipo === 'FIBROSCAN') {
      if (paciente.ultimo_test.resultado === 'ALTO' || paciente.ultimo_test.resultado === 'CRITICO') {
        return {
          necesitaDerivacion: true,
          categoriaDestino: 'C3',
          motivo: 'FIBROSCAN alto indica necesidad de tratamiento C3'
        };
      }
    }
    
    // Verificar si tiene múltiples consultas sin mejoría
    if (paciente.estadisticas && paciente.estadisticas.total_consultas >= 3) {
      if (paciente.estadisticas.sin_mejoria) {
        return {
          necesitaDerivacion: true,
          categoriaDestino: 'C3',
          motivo: 'Múltiples consultas sin mejoría, requiere evaluación C3'
        };
      }
    }
  }
  
  // M3 (C3) no deriva a categoría superior
  if (categoriaMedico === 'C3') {
    return {
      necesitaDerivacion: false,
      categoriaDestino: null,
      motivo: 'Médico C3 es la categoría más alta'
    };
  }
  
  return {
    necesitaDerivacion: false,
    categoriaDestino: null,
    motivo: 'No se requiere derivación'
  };
};

/**
 * Obtiene el texto del botón de derivación basado en la categoría de destino
 * @param {string} categoriaDestino - Categoría a la que se derivará
 * @returns {string} - Texto del botón
 */
export const getTextoBotonDerivacion = (categoriaDestino) => {
  switch (categoriaDestino) {
    case 'C2':
      return 'Derivar a C2';
    case 'C3':
      return 'Derivar a C3';
    default:
      return 'Derivar';
  }
};

/**
 * Obtiene el color del botón de derivación basado en la categoría de destino
 * @param {string} categoriaDestino - Categoría a la que se derivará
 * @returns {string} - Color del botón
 */
export const getColorBotonDerivacion = (categoriaDestino) => {
  switch (categoriaDestino) {
    case 'C2':
      return 'orange';
    case 'C3':
      return 'red';
    default:
      return 'blue';
  }
};

/**
 * Verifica si un paciente puede ser derivado por el médico actual
 * @param {Object} paciente - Objeto paciente
 * @param {string} categoriaMedico - Categoría del médico actual
 * @returns {boolean} - Si puede ser derivado
 */
export const puedeSerDerivado = (paciente, categoriaMedico) => {
  const derivacion = necesitaDerivacion(paciente, categoriaMedico);
  return derivacion.necesitaDerivacion;
};

/**
 * Obtiene la información completa de derivación para un paciente
 * @param {Object} paciente - Objeto paciente
 * @param {string} categoriaMedico - Categoría del médico actual
 * @returns {Object} - Información completa de derivación
 */
export const getInfoDerivacion = (paciente, categoriaMedico) => {
  const derivacion = necesitaDerivacion(paciente, categoriaMedico);
  
  return {
    ...derivacion,
    textoBoton: getTextoBotonDerivacion(derivacion.categoriaDestino),
    colorBoton: getColorBotonDerivacion(derivacion.categoriaDestino),
    puedeDerivar: derivacion.necesitaDerivacion
  };
};
