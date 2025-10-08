// src/router/ProtectedRoute.jsx

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

  if (allowedRoles && !allowedRoles.includes(user.tipo_usuario)) {
    console.warn(
      `[PROTECTED ROUTE] Usuario con rol '${user.tipo_usuario}' no autorizado. Redirigiendo a login.`
    );
    return <Navigate to="/login" replace />;
  }

  console.log("[PROTECTED ROUTE] Acceso permitido. Renderizando contenido.");
  return children;
};

export default ProtectedRoute;
