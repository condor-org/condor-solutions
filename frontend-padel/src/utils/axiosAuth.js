// src/utils/axiosAuth.js
import axios from "axios";
import { applyAuthInterceptor } from "../auth/axiosInterceptor";
import { API_BASE_URL } from "../config/runtime";

export const axiosAuth = (token) => {
  const instance = axios.create({
    baseURL: API_BASE_URL, // "/api"
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  // logs útiles y sin undefined
  instance.interceptors.request.use((config) => {
    const base = config.baseURL?.replace(/\/+$/, "") || "";
    const url  = `${base}${config.url || ""}`;
    console.log("[AXIOS REQUEST]", config.method?.toUpperCase(), url, "Auth:", !!config.headers?.Authorization);
    return config;
  });

  applyAuthInterceptor(instance);
  return instance;
};
