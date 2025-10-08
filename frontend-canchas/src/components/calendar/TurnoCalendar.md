# TurnoCalendar

Wrapper de FullCalendar con estilos Chakra, tokens visuales y diseño mobile-first.

## Props

- `events`: array — lista de eventos en formato FullCalendar
- `onEventClick`: function — callback al hacer click en evento
- `height`: número — altura del calendario (default: 500)
- `slotMinTime`: string — hora mínima (default: '07:00:00')
- `slotMaxTime`: string — hora máxima (default: '23:00:00')

## Diseño

- Mobile-first con paddings responsivos
- Tokens visuales (`useColorModeValue`)
- Layout fluido y accesible
- Preparado para tematización futura (colores por sede, etc.)

## Uso

```jsx
<TurnoCalendar
  events={turnos}
  onEventClick={handleEventClick}
/>
