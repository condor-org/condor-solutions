// src/utils.axiosAuth.js

import axios from "axios";
import { applyAuthInterceptor } from '../auth/axiosInterceptor';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;
const DEBUG_LOG = process.env.REACT_APP_DEBUG_LOG_REQUESTS === 'true';

export const axiosAuth = (token) => {
  const instance = axios.create({
    baseURL: `${API_BASE_URL}/api/`,
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  applyAuthInterceptor(instance); // 👈 Interceptor para expiración local y logout

  if (DEBUG_LOG) {
    instance.interceptors.request.use(config => {
      console.debug(
        `[FRONTEND] inicia llamada a endpoint: ${config.baseURL}${config.url}`
      );
      if (config.data) {
        console.debug('[FRONTEND] payload:', config.data);
      }
      return config;
    });

    instance.interceptors.response.use(
      response => {
        console.debug(
          `[FRONTEND] respuesta de ${response.config.url}:`,
          response.data
        );
        return response;
      },
      error => {
        if (error.response) {
          console.debug(
            `[FRONTEND] error en ${error.response.config.url}:`,
            error.response.data
          );
        } else {
          console.debug('[FRONTEND] request error:', error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  return instance;
};
