// src/router/PublicRoute.jsx

import React, { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthContext";

const PublicRoute = ({ children }) => {
  const { user, loadingUser } = useContext(AuthContext);

  console.log("[PUBLIC ROUTE] Render. user:", user, "loadingUser:", loadingUser);

  if (loadingUser) {
    return null; // O un loader/spinner si prefieres
  }

  if (user?.tipo_usuario) {
    const destino =
      user.tipo_usuario === "super_admin" ||
      user.tipo_usuario === "admin_cliente"
        ? "/admin"
        : "/jugador";

    console.log("[PUBLIC ROUTE] Usuario logueado. Redireccionando a:", destino);
    return <Navigate to={destino} replace />;
  }

  console.log("[PUBLIC ROUTE] Usuario no logueado. Renderizando children.");
  return children;
};

export default PublicRoute;
