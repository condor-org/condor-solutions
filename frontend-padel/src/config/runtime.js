// src/config/runtime.js
const rc = window.RUNTIME_CONFIG || {};
export const API_BASE_URL       = rc.API_BASE_URL || '/api';
export const CLIENTE_ID         = String(rc.CLIENTE_ID || '1');
export const NOMBRE_CLIENTE     = rc.NOMBRE_CLIENTE || 'Condor';
export const COLOR_PRIMARIO     = rc.COLOR_PRIMARIO || '#F44336';
export const COLOR_SECUNDARIO   = rc.COLOR_SECUNDARIO || '#000000';
