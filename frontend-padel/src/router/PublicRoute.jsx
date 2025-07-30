// src/router/PublicRoute.jsx

import React, { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthContext";

const PublicRoute = ({ children }) => {
  const { user, loadingUser } = useContext(AuthContext);

  console.log("[PUBLIC ROUTE] Render. user:", user, "loadingUser:", loadingUser);

  if (loadingUser) return null;

  if (user?.tipo_usuario) {
    let destino = "/login"; // fallback defensivo

    switch (user.tipo_usuario) {
      case "super_admin":
      case "admin_cliente":
        destino = "/admin";
        break;
      case "usuario_final":
        destino = "/jugador";
        break;
      case "empleado_cliente":
        destino = "/profesores/turnos";
        break;
      default:
        console.warn("[PUBLIC ROUTE] ⚠️ tipo_usuario desconocido:", user.tipo_usuario);
    }

    console.log("[PUBLIC ROUTE] Usuario logueado. Redireccionando a:", destino);
    return <Navigate to={destino} replace />;
  }

  console.log("[PUBLIC ROUTE] Usuario no logueado. Renderizando children.");
  return children;
};

export default PublicRoute;
