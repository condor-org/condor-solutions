// src/components/calendar/TurnoCalendar.jsx
import React, { useMemo } from 'react';
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

  // Mantiene el comportamiento de desktop, mejora móvil
  const initialView = useMemo(
    () => (isMobile ? 'timeGridDay' : 'timeGridWeek'),
    [isMobile]
  );

  const calendarHeight = useMemo(
    () => (isMobile ? 'auto' : height),
    [isMobile, height]
  );

  const headerToolbar = useMemo(
    () =>
      isMobile
        ? { left: 'prev,next', center: 'title', right: '' }
        : { left: 'prev,next today', center: 'title', right: '' },
    [isMobile]
  );

  const dayHeaderFormat = useMemo(
    () =>
      isMobile
        ? { weekday: 'short', day: 'numeric' }
        : { weekday: 'short', day: '2-digit', month: '2-digit' },
    [isMobile]
  );

  const slotLabelFormat = useMemo(
    () => ({
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }),
    []
  );

  return (
    <Box
      bg={bg}
      borderRadius="md"
      boxShadow="lg"
      p={{ base: 3, md: 6 }}
      border="1px solid"
      borderColor={border}
      color={text}
      // En móvil permitimos scroll horizontal del grid si hace falta
      overflowX={{ base: 'auto', md: 'hidden' }}
      // Ajustes mínimos de tipografía en mobile para que no se corte
      sx={{
        '.fc': { fontSize: isMobile ? '0.85rem' : '1rem' },
        '.fc .fc-toolbar-title': { fontSize: isMobile ? '1rem' : '1.25rem' },
        '.fc .fc-timegrid-slot-label': { padding: isMobile ? '0 4px' : '0 8px' },
      }}
    >
      <FullCalendar
        plugins={[timeGridPlugin, dayGridPlugin, interactionPlugin]}
        initialView={initialView}
        locale="es"
        headerToolbar={headerToolbar}
        height={calendarHeight}
        contentHeight="auto"
        expandRows
        events={events}
        eventClick={onEventClick}
        slotMinTime={slotMinTime}
        slotMaxTime={slotMaxTime}
        nowIndicator
        allDaySlot={false}
        slotDuration="00:30:00"
        slotLabelFormat={slotLabelFormat}
        dayHeaderFormat={dayHeaderFormat}
        // Gestos más amigables en touch
        longPressDelay={300}
        handleWindowResize
      />
    </Box>
  );
};

export default TurnoCalendar;
