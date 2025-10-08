# SummaryCard

Tarjeta visual para dashboards con ícono, título y valor. Adaptable a modo claro/oscuro y mobile-first.

## Props

- `title`: string — título de la tarjeta
- `value`: string | number — valor principal
- `icon`: React icon — ícono visual (ej: `FaCalendarCheck`)
- `bg`: string — color de fondo (opcional)
- `color`: string — color de texto (opcional)
- `iconColor`: string — color del ícono (opcional)
- `maxW`: string — ancho máximo (default: 300px)
- `minW`: string — ancho mínimo (default: 220px)

## Diseño

- Mobile-first con paddings y fuentes responsivas
- Tokens visuales (`useColorModeValue`)
- Layout fluido y accesible
- Ideal para paneles de usuario o admin

## Uso

```jsx
<SummaryCard
  title="Turnos reservados"
  value={12}
  icon={FaCalendarCheck}
  bg="white"
  color="gray.800"
  iconColor="blue.500"
/>
