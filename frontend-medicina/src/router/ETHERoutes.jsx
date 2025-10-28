import React from 'react';
import { Routes, Route } from 'react-router-dom';

// Importar todas las vistas
// Médico M1
import DashboardM1 from '../pages/medico-m1/DashboardM1';
import IngresarPaciente from '../pages/medico-m1/IngresarPaciente';
import PacientesM1 from '../pages/medico-m1/PacientesM1';

// Médico M2
import AgendaM2 from '../pages/medico-m2/AgendaM2';

// Médico M3
import AgendaM3 from '../pages/medico-m3/AgendaM3';

// Admin Ministro
import DashboardMinistro from '../pages/admin-ministro/DashboardMinistro';
import EstablecimientosPage from '../pages/admin-ministro/EstablecimientosPage';

// Admin Establecimiento
import DashboardEstablecimiento from '../pages/admin-establecimiento/DashboardEstablecimiento';
import MedicosPage from '../pages/admin-establecimiento/MedicosPage';

// Paciente
import DashboardPaciente from '../pages/paciente/DashboardPaciente';
import MisTurnos from '../pages/paciente/MisTurnos';
import MiHistorial from '../pages/paciente/MiHistorial';

const ETHERoutes = () => {
  return (
    <Routes>
      {/* Rutas Médico M1 */}
      <Route path="medico-m1" element={<DashboardM1 />} />
      <Route path="medico-m1/dashboard" element={<DashboardM1 />} />
      <Route path="medico-m1/ingresar-paciente" element={<IngresarPaciente />} />
      <Route path="medico-m1/pacientes" element={<PacientesM1 />} />
      
      {/* Rutas Médico M2 */}
      <Route path="medico-m2" element={<AgendaM2 />} />
      <Route path="medico-m2/agenda" element={<AgendaM2 />} />
      
      {/* Rutas Médico M3 */}
      <Route path="medico-m3" element={<AgendaM3 />} />
      <Route path="medico-m3/agenda" element={<AgendaM3 />} />
      
      {/* Rutas Admin Ministro */}
      <Route path="admin-ministro" element={<DashboardMinistro />} />
      <Route path="admin-ministro/dashboard" element={<DashboardMinistro />} />
      <Route path="admin-ministro/establecimientos" element={<EstablecimientosPage />} />
      
      {/* Rutas Admin Establecimiento */}
      <Route path="admin-establecimiento" element={<DashboardEstablecimiento />} />
      <Route path="admin-establecimiento/dashboard" element={<DashboardEstablecimiento />} />
      <Route path="admin-establecimiento/medicos" element={<MedicosPage />} />
      
      {/* Rutas Paciente */}
      <Route path="paciente" element={<DashboardPaciente />} />
      <Route path="paciente/dashboard" element={<DashboardPaciente />} />
      <Route path="paciente/mis-turnos" element={<MisTurnos />} />
      <Route path="paciente/mi-historial" element={<MiHistorial />} />
    </Routes>
  );
};

export default ETHERoutes;
