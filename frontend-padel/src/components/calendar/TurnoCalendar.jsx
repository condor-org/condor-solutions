// src/components/calendar/TurnoCalendar.jsx
import React from 'react';
import { Box, useColorModeValue, useBreakpointValue } from '@chakra-ui/react';
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';

const TurnoCalendar = ({
  events = [],
  onEventClick,
  height = 500,
  slotMinTime = '07:00:00',
  slotMaxTime = '23:00:00',
  diasDisponibles = [], // Días de la semana disponibles del profesor
  profesorId, // ID del profesor seleccionado
}) => {
  const bg = useColorModeValue('white', 'gray.800');
  const border = useColorModeValue('gray.200', 'gray.700');
  const text = useColorModeValue('gray.800', 'white');

  const isMobile = useBreakpointValue({ base: true, md: false });

  // Función para deshabilitar días no disponibles del profesor
  const dayCellClassNames = (info) => {
    if (!profesorId || diasDisponibles.length === 0) {
      return []; // Si no hay profesor seleccionado o no hay filtro, mostrar todos los días
    }
    
    const diaSemana = info.date.getDay(); // 0 = domingo, 1 = lunes, etc.
    const esDisponible = diasDisponibles.includes(diaSemana);
    
    if (!esDisponible) {
      return ['fc-day-disabled']; // Clase CSS para deshabilitar el día
    }
    
    return [];
  };

  // Desktop: exactamente igual que antes
  const headerDesktop = { left: 'prev,next today', center: 'title', right: '' };
  const headerMobile  = { left: 'prev,next', center: 'title', right: 'today' };

  return (
    <Box
      bg={bg}
      borderRadius="md"
      boxShadow="lg"
      p={{ base: 3, md: 6 }}
      border="1px solid"
      borderColor={border}
      color={text}
      overflow="hidden"
    >
      {/* En mobile, permitir scroll horizontal del calendario completo */}
      <Box
        overflowX={{ base: 'auto', md: 'visible' }}
        /* min-width para que 7 columnas no se aplasten en mobile.
           840px ~ 7 días x ~120px c/u (ajustable). */
        sx={{
          '& .fc': { minWidth: { base: '840px', md: 'auto' } },
          /* Compactar sólo en mobile */
          '& .fc-toolbar-title': { fontSize: { base: 'md', md: 'xl' } },
          '& .fc .fc-button': {
            fontSize: { base: 'xs', md: 'sm' },
            padding: { base: '2px 6px', md: '6px 10px' },
            lineHeight: { base: '1.1', md: '1.2' },
          },
          '& .fc-col-header-cell-cushion': { fontSize: { base: 'xs', md: 'sm' }, padding: { base: '6px 0', md: '8px 0' } },
          '& .fc-timegrid-slot-label': { fontSize: { base: 'xs', md: 'sm' } },
          '& .fc-timegrid-axis-cushion': { fontSize: { base: 'xs', md: 'sm' } },
          '& .fc .fc-toolbar.fc-header-toolbar': { marginBottom: { base: '6px', md: '12px' } },
          '& .fc-timegrid-event': { borderRadius: '8px' },
          '& .fc-scrollgrid, & .fc-timegrid-body': { borderRadius: '8px' },
          /* Estilos para días no disponibles del profesor */
          '& .fc-day-disabled': {
            backgroundColor: '#f5f5f5 !important',
            color: '#999 !important',
            cursor: 'not-allowed !important',
            opacity: '0.5 !important',
          },
          '& .fc-day-disabled .fc-daygrid-day-number': {
            color: '#999 !important',
          },
          '& .fc-day-disabled .fc-timegrid-slot': {
            backgroundColor: '#f5f5f5 !important',
          },
        }}
      >
        <FullCalendar
          plugins={[timeGridPlugin, dayGridPlugin, interactionPlugin]}
          locale="es"
          initialView="timeGridWeek"                  // 👈 sigue siendo semana en mobile y desktop
          headerToolbar={isMobile ? headerMobile : headerDesktop}
          height={isMobile ? 'auto' : height}
          contentHeight="auto"
          expandRows
          stickyHeaderDates
          events={events}
          eventClick={onEventClick}
          slotMinTime={slotMinTime}
          slotMaxTime={slotMaxTime}
          slotDuration="00:30:00"
          slotLabelFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
          // Formatos más cortos en mobile
          dayHeaderFormat={isMobile ? { weekday: 'narrow', day: '2-digit' } : { weekday: 'short', day: '2-digit', month: '2-digit' }}
          buttonText={{ today: 'hoy' }}
          nowIndicator
          allDaySlot={false}
          // opcional: arrancar scrolleado cerca de ahora para mobile
          scrollTime={isMobile ? new Date().toTimeString().slice(0,5) : undefined}
          // Filtrar días disponibles del profesor
          dayCellClassNames={dayCellClassNames}
        />
      </Box>
    </Box>
  );
};

export default TurnoCalendar;
