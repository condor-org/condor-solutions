// src/App.jsx
import './styles/globals.css';
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./router/ProtectedRoute";

import LoginPage from "./pages/auth/LoginPage";
import RegistroPage from "./pages/auth/RegistroPage";

import DashboardPage from "./pages/admin/DashboardPage";
import ConfiguracionPagoPage from "./pages/admin/ConfiguracionPagoPage";
import SedesPage from "./pages/admin/SedesPage";
import ProfesoresPage from "./pages/admin/ProfesoresPage";
import UsuariosPage from "./pages/admin/UsuariosPage";
import PagosPreaprobadosPage from "./pages/admin/PagosPreaprobadosPage";
import JugadorDashboard from "./pages/user/JugadorDashboard";
import PerfilPage from "./pages/user/PerfilPage";
import ReservarTurno from "./pages/user/ReservarTurno";

import NotFoundPage from "./pages/NotFoundPage";

function App() {
  return (
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
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/configuracion-pago"
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <ConfiguracionPagoPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/sedes"
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <SedesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/profesores"
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <ProfesoresPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/usuarios"
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <UsuariosPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/pagos-preaprobados"
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <PagosPreaprobadosPage />
            </ProtectedRoute>
          }
        />

        {/* Jugador */}
        <Route
          path="/jugador"
          element={
            <ProtectedRoute allowedRoles={["jugador"]}>
              <JugadorDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reservar"
          element={
            <ProtectedRoute allowedRoles={["jugador"]}>
              <ReservarTurno />
            </ProtectedRoute>
          }
        />
        <Route
          path="/perfil"
          element={
            <ProtectedRoute allowedRoles={["jugador", "admin"]}>
              <PerfilPage />
            </ProtectedRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>

      <ToastContainer position="top-right" autoClose={3000} />
    </>
  );
}

export default App;
