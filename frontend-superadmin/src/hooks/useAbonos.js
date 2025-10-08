import { useMemo } from 'react';
import usePaginatedData from './usePaginatedData';

/**
 * Hook específico para cargar abonos con paginación automática
 * @param {Object} api - Instancia de axios configurada
 * @param {Object} filters - Filtros para la búsqueda
 * @returns {Object} { abonos, loading, error, refetch }
 */
export const useAbonos = (api, filters = {}) => {
  const fetchFunction = useMemo(() => {
    if (!api) return null;
    
    return async (params) => {
      return await api.get('padel/abonos/', { params });
    };
  }, [api]);

  const { data: abonos, loading, error, refetch } = usePaginatedData(
    fetchFunction,
    filters,
    [JSON.stringify(filters)]
  );

  return { abonos, loading, error, refetch };
};

export default useAbonos;
