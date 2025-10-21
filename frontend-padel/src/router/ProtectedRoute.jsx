// src/router/ProtectedRoute.jsx
/**
 * Componente para rutas protegidas con autorización por roles.
 * Verifica que el usuario tenga el rol necesario para acceder a la ruta.
 */
import React, { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthContext";

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loadingUser } = useContext(AuthContext);

  if (loadingUser) {
    console.log("[PROTECTED ROUTE] Esperando fin de carga de usuario...");
    return null;  // Aquí podrías mostrar un spinner en lugar de null
  }

  if (!user) {
    console.warn("[PROTECTED ROUTE] Usuario no autenticado. Redirigiendo a login.");
    return <Navigate to="/login" replace />;
  }

  // Obtener el rol actual del usuario (usar cliente_actual.rol - nueva estructura multi-tenant)
  const currentRole = user.cliente_actual?.rol;
  
  if (allowedRoles && !allowedRoles.includes(currentRole)) {
    console.warn(
      `[PROTECTED ROUTE] Usuario con rol '${currentRole}' no autorizado. Redirigiendo a login.`
    );
    return <Navigate to="/login" replace />;
  }

  console.log("[PROTECTED ROUTE] Acceso permitido. Renderizando contenido.");
  return children;
};

export default ProtectedRoute;
