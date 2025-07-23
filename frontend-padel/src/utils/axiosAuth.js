// src/utils.axiosAuth.js

import axios from "axios";
import { applyAuthInterceptor } from '../auth/axiosInterceptor';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

export const axiosAuth = (token) => {
  const instance = axios.create({
    baseURL: `${API_BASE_URL}/api/`,
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  applyAuthInterceptor(instance); // 👈 Interceptor para expiración local y logout

  return instance;
};
