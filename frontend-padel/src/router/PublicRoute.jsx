// src/router/PublicRoute.jsx
/**
 * Componente para rutas públicas con redirección automática.
 * Redirige usuarios autenticados a su dashboard según su rol actual.
 */
import React, { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthContext";

const PublicRoute = ({ children }) => {
  const { user, loadingUser } = useContext(AuthContext);

  console.log("[PUBLIC ROUTE] Render. user:", user, "loadingUser:", loadingUser);
  console.log("[PUBLIC ROUTE] user?.cliente_actual:", user?.cliente_actual);
  console.log("[PUBLIC ROUTE] user?.cliente_actual?.rol:", user?.cliente_actual?.rol);
  console.log("[PUBLIC ROUTE] user keys:", user ? Object.keys(user) : "user is null");

  if (loadingUser) return null;

  // Verificar si el usuario está autenticado (tiene id y cliente_actual)
  if (user?.id && user?.cliente_actual?.rol) {
    let destino = "/login"; // fallback defensivo

    // Usar la estructura actual del usuario (cliente_actual.rol)
    const currentRole = user.cliente_actual.rol;

    console.log("[PUBLIC ROUTE] Usuario autenticado con cliente_actual.rol:", currentRole);

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
        console.warn("[PUBLIC ROUTE] ⚠️ cliente_actual.rol desconocido:", currentRole);
        // Fallback: si no reconoce el rol, redirigir a jugador
        destino = "/jugador";
    }

    console.log("[PUBLIC ROUTE] Usuario logueado. Redireccionando a:", destino);
    return <Navigate to={destino} replace />;
  }

  console.log("[PUBLIC ROUTE] Usuario no logueado. Renderizando children.");
  return children;
};

export default PublicRoute;
