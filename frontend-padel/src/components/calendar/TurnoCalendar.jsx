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
}) => {
  const bg = useColorModeValue('white', 'gray.800');
  const border = useColorModeValue('gray.200', 'gray.700');
  const text = useColorModeValue('gray.800', 'white');

  const isMobile = useBreakpointValue({ base: true, md: false });

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
        />
      </Box>
    </Box>
  );
};

export default TurnoCalendar;
