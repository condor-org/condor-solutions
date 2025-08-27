// src/utils/axiosAuth.js
import axios from "axios";
import { applyAuthInterceptor } from "../auth/axiosInterceptor";
import { API_BASE_URL } from "../config/runtime";

export const axiosAuth = (token) => {
  const instance = axios.create({
    baseURL: API_BASE_URL, // ej: "/api"
    headers: { Authorization: `Bearer ${token}` },
  });
  applyAuthInterceptor(instance);
  return instance;
};
