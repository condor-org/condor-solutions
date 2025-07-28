# TurnoSelector

Componente desacoplado para seleccionar sede y profesor, con diseño mobile-first y tematización por tokens.

## Props

- `sedes`: array — lista de sedes disponibles
- `profesores`: array — lista de profesores disponibles
- `sedeId`: string — ID de sede seleccionada
- `profesorId`: string — ID de profesor seleccionado
- `onSedeChange`: function — callback al cambiar sede
- `onProfesorChange`: function — callback al cambiar profesor
- `disabled`: boolean — desactiva el selector de profesor

## Diseño

- Mobile-first (`Stack` con `direction` adaptable)
- Tokens visuales (`useColorModeValue`)
- Layout fluido y accesible
- Ideal para filtros, formularios o dashboards

## Uso

```jsx
<TurnoSelector
  sedes={sedes}
  profesores={profesores}
  sedeId={sedeId}
  profesorId={profesorId}
  onSedeChange={setSedeId}
  onProfesorChange={setProfesorId}
/>
