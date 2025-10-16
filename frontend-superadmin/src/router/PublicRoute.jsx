// src/router/PublicRoute.jsx
/**
 * Componente para rutas públicas con redirección automática.
 * Redirige usuarios autenticados a su dashboard según su rol actual.
 * Soporta tanto estructura antigua (tipo_usuario) como nueva (cliente_actual.rol).
 */
import React, { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthContext";

const PublicRoute = ({ children }) => {
  const { user, loadingUser } = useContext(AuthContext);

  console.log("[PUBLIC ROUTE] Render. user:", user, "loadingUser:", loadingUser);

  if (loadingUser) return null;

  if (user?.tipo_usuario || user?.cliente_actual?.rol) {
    let destino = "/login"; // fallback defensivo

    // Usar la nueva estructura multi-tenant primero, luego fallback a la antigua
    const currentRole = user.cliente_actual?.rol || user.tipo_usuario;

    switch (currentRole) {
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
        console.warn("[PUBLIC ROUTE] ⚠️ rol desconocido:", currentRole);
    }

    console.log("[PUBLIC ROUTE] Usuario logueado. Redireccionando a:", destino);
    return <Navigate to={destino} replace />;
  }

  console.log("[PUBLIC ROUTE] Usuario no logueado. Renderizando children.");
  return children;
};

export default PublicRoute;
