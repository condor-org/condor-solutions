import { useState, useEffect, useCallback } from 'react';

/**
 * Hook para manejar datos paginados de APIs
 * @param {Function} fetchFunction - Función que hace la llamada a la API
 * @param {Object} params - Parámetros para la llamada
 * @param {Array} dependencies - Dependencias para re-fetch
 * @returns {Object} { data, loading, error, refetch }
 */
export const usePaginatedData = (fetchFunction, params = {}, dependencies = []) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAllData = useCallback(async () => {
    if (!fetchFunction) return;
    
    setLoading(true);
    setError(null);
    
    try {
      let allResults = [];
      let offset = 0;
      const limit = 50; // Tamaño de página razonable
      let hasMore = true;

      while (hasMore) {
        const currentParams = {
          ...params,
          limit,
          offset
        };

        const response = await fetchFunction(currentParams);
        const results = Array.isArray(response?.data) 
          ? response.data 
          : (response?.data?.results ?? []);

        allResults = [...allResults, ...results];

        // Verificar si hay más páginas
        if (response?.data?.next) {
          offset += limit;
        } else {
          hasMore = false;
        }

        // Protección contra bucles infinitos
        if (offset > 10000) {
          console.warn('usePaginatedData: Límite de offset alcanzado, deteniendo paginación');
          hasMore = false;
        }
      }

      setData(allResults);
    } catch (err) {
      console.error('Error fetching paginated data:', err);
      setError(err);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [fetchFunction, JSON.stringify(params), ...dependencies]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  const refetch = useCallback(() => {
    fetchAllData();
  }, [fetchAllData]);

  return { data, loading, error, refetch };
};

export default usePaginatedData;
