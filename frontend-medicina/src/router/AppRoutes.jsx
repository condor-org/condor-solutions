import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

// Importar componentes de layout
import { ETHELayout, ETHERedirect } from '../components/ethe';

// Importar páginas ETHE
import DashboardM1 from '../pages/medico-m1/DashboardM1';
import IngresarPaciente from '../pages/medico-m1/IngresarPaciente';
import PacientesM1 from '../pages/medico-m1/PacientesM1';
import AgendaM2 from '../pages/medico-m2/AgendaM2';
import DashboardM2 from '../pages/medico-m2/DashboardM2';
import PacientesM2 from '../pages/medico-m2/PacientesM2';
import AgendaM3 from '../pages/medico-m3/AgendaM3';
import DashboardM3 from '../pages/medico-m3/DashboardM3';
import PacientesM3 from '../pages/medico-m3/PacientesM3';
import DashboardMinistro from '../pages/admin-ministro/DashboardMinistro';
import EstablecimientosPage from '../pages/admin-ministro/EstablecimientosPage';
import ListaPacientesPage from '../pages/admin-ministro/ListaPacientesPage';
import DashboardEstablecimiento from '../pages/admin-establecimiento/DashboardEstablecimiento';
import MedicosPage from '../pages/admin-establecimiento/MedicosPage';
import DashboardPaciente from '../pages/paciente/DashboardPaciente';
import MisTurnos from '../pages/paciente/MisTurnos';
import MiHistorial from '../pages/paciente/MiHistorial';
import SeguimientoPaciente from '../pages/comun/SeguimientoPaciente';
import AdminMinistroRoute from '../components/ethe/AdminMinistroRoute';

// Importar páginas de autenticación existentes
import LoginPage from '../pages/auth/LoginPage';
import ForgotPasswordPage from '../pages/auth/ForgotPasswordPage';
import RegisterPage from '../pages/auth/RegisterPage';

// Componente para rutas protegidas
const ProtectedRoute = ({ children }) => {
  const { user, loadingUser } = useAuth();
  
  console.log('🔒 ProtectedRoute: Componente montado');
  console.log('👤 ProtectedRoute: User:', user);
  console.log('⏳ ProtectedRoute: Loading:', loadingUser);
  
  if (loadingUser) {
    console.log('⏳ ProtectedRoute: Mostrando loading...');
    return (
      <ETHELayout loading={true}>
        <div>Loading...</div>
      </ETHELayout>
    );
  }
  
  if (!user) {
    console.log('❌ ProtectedRoute: No hay usuario, redirigiendo a login');
    return <Navigate to="/login" replace />;
  }
  
  console.log('✅ ProtectedRoute: Usuario autenticado, renderizando contenido');
  return <ETHELayout>{children}</ETHELayout>;
};

// Componente para rutas públicas
const PublicRoute = ({ children }) => {
  const { user, loadingUser } = useAuth();
  
  if (loadingUser) {
    return <div>Loading...</div>;
  }
  
  if (user) {
    return <ETHERedirect />;
  }
  
  return children;
};

const AppRoutes = () => {
  return (
    <Routes>
      {/* Rutas públicas */}
      <Route 
        path="/login" 
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        } 
      />
      <Route 
        path="/forgot-password" 
        element={
          <PublicRoute>
            <ForgotPasswordPage />
          </PublicRoute>
        } 
      />
      <Route 
        path="/register" 
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        } 
      />
      
      {/* Redirección por defecto */}
      <Route path="/" element={<ETHERedirect />} />
      
      {/* Rutas protegidas ETHE */}
      <Route 
        path="/medico-m1" 
        element={
          <ProtectedRoute>
            <DashboardM1 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m1/dashboard" 
        element={
          <ProtectedRoute>
            <DashboardM1 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m1/ingresar-paciente" 
        element={
          <ProtectedRoute>
            <IngresarPaciente />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m1/pacientes" 
        element={
          <ProtectedRoute>
            <PacientesM1 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m2" 
        element={
          <ProtectedRoute>
            <DashboardM2 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m2/dashboard" 
        element={
          <ProtectedRoute>
            <DashboardM2 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m2/agenda" 
        element={
          <ProtectedRoute>
            <AgendaM2 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m2/pacientes" 
        element={
          <ProtectedRoute>
            <PacientesM2 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m3" 
        element={
          <ProtectedRoute>
            <DashboardM3 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m3/dashboard" 
        element={
          <ProtectedRoute>
            <DashboardM3 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m3/agenda" 
        element={
          <ProtectedRoute>
            <AgendaM3 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/medico-m3/pacientes" 
        element={
          <ProtectedRoute>
            <PacientesM3 />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin-ministro" 
        element={
          <ProtectedRoute>
            <DashboardMinistro />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin-ministro/dashboard" 
        element={
          <ProtectedRoute>
            <DashboardMinistro />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin-ministro/establecimientos" 
        element={
          <ProtectedRoute>
            <EstablecimientosPage />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin-ministro/seguimiento-pacientes" 
        element={
          <ProtectedRoute>
            <ListaPacientesPage />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin-establecimiento" 
        element={
          <ProtectedRoute>
            <DashboardEstablecimiento />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin-establecimiento/dashboard" 
        element={
          <ProtectedRoute>
            <DashboardEstablecimiento />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin-establecimiento/medicos" 
        element={
          <ProtectedRoute>
            <MedicosPage />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/paciente" 
        element={
          <ProtectedRoute>
            <DashboardPaciente />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/paciente/dashboard" 
        element={
          <ProtectedRoute>
            <DashboardPaciente />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/paciente/mis-turnos" 
        element={
          <ProtectedRoute>
            <MisTurnos />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/paciente/mi-historial" 
        element={
          <ProtectedRoute>
            <MiHistorial />
          </ProtectedRoute>
        } 
      />
      
      {/* Ruta para seguimiento de paciente */}
      <Route 
        path="/seguimiento-paciente/:pacienteId" 
        element={
          <ProtectedRoute>
            <SeguimientoPaciente />
          </ProtectedRoute>
        } 
      />
      
      {/* Ruta catch-all para redirección */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;