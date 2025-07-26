// src/components/calendar/TurnoCalendar.jsx

import React from 'react';
import { Box, useColorModeValue } from '@chakra-ui/react';
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

  return (
    <Box
      bg={bg}
      borderRadius="md"
      boxShadow="lg"
      p={{ base: 4, md: 6 }}
      border="1px solid"
      borderColor={border}
      color={text}
      overflow="hidden"
    >
      <FullCalendar
        plugins={[timeGridPlugin, dayGridPlugin, interactionPlugin]}
        initialView="timeGridWeek"
        locale="es"
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: '',
        }}
        height={height}
        events={events}
        eventClick={onEventClick}
        slotMinTime={slotMinTime}
        slotMaxTime={slotMaxTime}
        nowIndicator
        allDaySlot={false}
        slotDuration="00:30:00"
        slotLabelFormat={{
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        }}
        dayHeaderFormat={{ weekday: "short", day: "2-digit", month: "2-digit" }}
        contentHeight="auto"
      />
    </Box>
  );
};

export default TurnoCalendar;
