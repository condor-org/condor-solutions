// src/router/AppRoutes.jsx

import React, { useContext } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthContext } from "../auth/AuthContext";
import ProtectedRoute from "../router/ProtectedRoute";
import PublicRoute from "../router/PublicRoute";

import LoginPage from "../pages/auth/LoginPage";
import RegistroPage from "../pages/auth/RegistroPage";

import DashboardPage from "../pages/admin/DashboardPage";
import SedesPage from "../pages/admin/SedesPage";
import ProfesoresPage from "../pages/admin/ProfesoresPage";
import UsuariosPage from "../pages/admin/UsuariosPage";
import PagosPreaprobadosPage from "../pages/admin/PagosPreaprobadosPage";
import CancelacionesPage from "../pages/admin/CancelacionesPage";
import JugadorDashboard from "../pages/user/JugadorDashboard";
import PerfilPage from "../pages/user/PerfilPage";
import ReservarTurno from "../pages/user/ReservarTurno";
import TurnosReservados from "../pages/profesores/TurnosReservados";

import NotFoundPage from "../pages/NotFoundPage";
import MainLayout from "../components/layout/MainLayout";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import NotificacionesPage from "../pages/user/NotificacionesPage";
import NotificacionesAdminPage from '../pages/admin/NotificacionesAdminPage';
import ReservarAbonoAdmin from "../pages/admin/ReservarAbonoAdmin";
import OAuthCallback from "../pages/auth/OAuthCallback";
import Signup from "../pages/auth/Signup";


// ...imports iguales...

const AppRoutes = () => {
  const { user } = useContext(AuthContext);
  const location = useLocation();

  console.log("[APP ROUTES] user actual:", user);
  console.log("[APP ROUTES] Ruta actual:", location.pathname);

  return (
    <>
      <Routes>
        {/* Home -> login por ahora */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* PÚBLICAS */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route
          path="/registro"
          element={
            <PublicRoute>
              <RegistroPage />
            </PublicRoute>
          }
        />
        <Route
          path="/signup"
          element={
            <PublicRoute>
              <Signup />
            </PublicRoute>
          }
        />

        {/* ⬇️ CALLBACK OAUTH **SIN WRAPPER** y en ambas variantes */}
        <Route path="/oauth/google/callback" element={<OAuthCallback />} />
        <Route path="/oauth/google/callback/" element={<OAuthCallback />} />

        {/* PRIVADAS */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute allowedRoles={["super_admin", "admin_cliente"]}>
              <MainLayout>
                <DashboardPage />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        {/* ...el resto de privadas igual... */}

        <Route path="*" element={<NotFoundPage />} />
      </Routes>

      <ToastContainer position="top-right" autoClose={3000} />
    </>
  );
};

export default AppRoutes;
