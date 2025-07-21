import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "../router/ProtectedRoute";

import LoginPage from "../pages/auth/LoginPage";
import RegistroPage from "../pages/auth/RegistroPage";

import DashboardPage from "../pages/admin/DashboardPage";
import ConfiguracionPagoPage from "../pages/admin/ConfiguracionPagoPage";
import SedesPage from "../pages/admin/SedesPage";
import ProfesoresPage from "../pages/admin/ProfesoresPage";
import UsuariosPage from "../pages/admin/UsuariosPage";
import PagosPreaprobadosPage from "../pages/admin/PagosPreaprobadosPage";

import JugadorDashboard from "../pages/user/JugadorDashboard";
import PerfilPage from "../pages/user/PerfilPage";
import ReservarTurno from "../pages/user/ReservarTurno";

import NotFoundPage from "../pages/NotFoundPage";
import MainLayout from "../components/layout/MainLayout"; // ✅ layout visual con navbar
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

const AppRoutes = () => (
  <>
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/registro" element={<RegistroPage />} />

      {/* Admin */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <MainLayout>
              <DashboardPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/configuracion-pago"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <MainLayout>
              <ConfiguracionPagoPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/sedes"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <MainLayout>
              <SedesPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/profesores"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <MainLayout>
              <ProfesoresPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/usuarios"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <MainLayout>
              <UsuariosPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/pagos-preaprobados"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <MainLayout>
              <PagosPreaprobadosPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      {/* Jugador */}
      <Route
        path="/jugador"
        element={
          <ProtectedRoute allowedRoles={["jugador"]}>
            <MainLayout>
              <JugadorDashboard />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reservar"
        element={
          <ProtectedRoute allowedRoles={["jugador"]}>
            <MainLayout>
              <ReservarTurno />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/perfil"
        element={
          <ProtectedRoute allowedRoles={["jugador", "admin"]}>
            <MainLayout>
              <PerfilPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>

    <ToastContainer position="top-right" autoClose={3000} />
  </>
);

export default AppRoutes;
