import { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { API_ENDPOINTS, getApiUrl } from '../config/api';

export const useApi = (endpoint, options = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { user } = useAuth();
  
  const fetchData = async (customOptions = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const url = getApiUrl(endpoint, customOptions.params || {});
      const config = {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(user?.token && { 'Authorization': `Bearer ${user.token}` }),
          ...customOptions.headers,
        },
        ...customOptions,
      };
      
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };
  
  return { data, loading, error, fetchData };
};

export const useApiMutation = (endpoint) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { user } = useAuth();
  
  const mutate = async (data, options = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const url = getApiUrl(endpoint, options.params || {});
      const config = {
        method: options.method || 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(user?.token && { 'Authorization': `Bearer ${user.token}` }),
          ...options.headers,
        },
        body: data ? JSON.stringify(data) : undefined,
        ...options,
      };
      
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };
  
  return { mutate, loading, error };
};

export default useApi;
