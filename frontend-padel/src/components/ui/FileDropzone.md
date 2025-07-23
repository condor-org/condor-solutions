# FileDropzone

Componente reutilizable para carga de archivos con visual moderno y tokens adaptables.

## Props

- `id`: string – identificador del input
- `label`: string – texto mostrado cuando no hay archivo
- `accept`: string – tipos de archivos permitidos
- `value`: File – archivo cargado
- `onChange`: function(File) – callback al seleccionar archivo
- `onRemove`: function – callback para quitar archivo
- `colorScheme`: string – tema visual (`green`, `blue`, `red`, etc.)

## Diseño

- Mobile-first con padding y layout adaptable
- Hover responsivo y accesible
- Ideal para comprobantes, imágenes de perfil, adjuntos

## Uso básico

```jsx
<FileDropzone
  label="Subí el comprobante"
  value={archivo}
  onChange={setArchivo}
  onRemove={() => setArchivo(null)}
  colorScheme="green"
/>
