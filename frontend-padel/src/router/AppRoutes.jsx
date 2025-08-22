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

const AppRoutes = () => {
  const { user } = useContext(AuthContext);
  const location = useLocation();

  console.log("[APP ROUTES] user actual:", user);
  console.log("[APP ROUTES] Ruta actual:", location.pathname);

  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

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

        {/* Admin (SuperAdmin o AdminCliente) */}
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
         <Route
          path="/admin/cancelaciones"
          element={
            <ProtectedRoute allowedRoles={["super_admin", "admin_cliente"]}>
              <MainLayout>
                <CancelacionesPage />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/sedes"
          element={
            <ProtectedRoute allowedRoles={["super_admin", "admin_cliente"]}>
              <MainLayout>
                <SedesPage />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/profesores"
          element={
            <ProtectedRoute allowedRoles={["super_admin", "admin_cliente"]}>
              <MainLayout>
                <ProfesoresPage />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/usuarios"
          element={
            <ProtectedRoute allowedRoles={["super_admin", "admin_cliente"]}>
              <MainLayout>
                <UsuariosPage />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/pagos-preaprobados"
          element={
            <ProtectedRoute allowedRoles={["super_admin", "admin_cliente"]}>
              <MainLayout>
                <PagosPreaprobadosPage />
              </MainLayout>
            </ProtectedRoute>
          }
        />

        {/* Jugador */}
        <Route
          path="/notificaciones"
          element={
            <ProtectedRoute allowedRoles={["usuario_final"]}>
              <MainLayout>
                <NotificacionesPage />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/jugador"
          element={
            <ProtectedRoute allowedRoles={["usuario_final"]}>
              <MainLayout>
                <JugadorDashboard />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/reservar"
          element={
            <ProtectedRoute allowedRoles={["usuario_final"]}>
              <MainLayout>
                <ReservarTurno />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/perfil"
          element={
            <ProtectedRoute allowedRoles={["usuario_final", "super_admin", "admin_cliente"]}>
              <MainLayout>
                <PerfilPage />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/profesores/turnos"
          element={
            <ProtectedRoute allowedRoles={["empleado_cliente"]}>
              <MainLayout>
                <TurnosReservados />
              </MainLayout>
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<NotFoundPage />} />
      </Routes>

      <ToastContainer position="top-right" autoClose={3000} />
    </>
  );
};

export default AppRoutes;
