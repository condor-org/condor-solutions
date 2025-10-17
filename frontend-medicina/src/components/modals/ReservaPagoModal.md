# ReservaPagoModal

Modal reutilizable para confirmar reserva de turno con comprobante de pago.

## Props

- `isOpen`: boolean — controla visibilidad
- `onClose`: función — cierra el modal
- `turno`: objeto — contiene fecha y hora del turno
- `configPago`: objeto — CBU, alias, monto, tiempo máximo
- `archivo`: File — comprobante cargado
- `onArchivoChange`: función — callback al subir archivo
- `onRemoveArchivo`: función — callback para quitar archivo
- `onConfirmar`: función — callback para confirmar reserva
- `loading`: boolean — estado de carga
- `tiempoRestante`: número — segundos restantes para subir comprobante

## Diseño

- Mobile-first (`size="xs"` en pantallas chicas)
- Tokens de color con `useColorModeValue`
- Layout fluido y accesible
- Preparado para integración con sistema de diseño global

## Uso

```jsx
<ReservaPagoModal
  isOpen={isOpen}
  onClose={onClose}
  turno={turnoSeleccionado}
  configPago={configPago}
  archivo={archivo}
  onArchivoChange={handleArchivoChange}
  onRemoveArchivo={handleRemoveArchivo}
  onConfirmar={handleConfirmarReserva}
  loading={isLoading}
  tiempoRestante={timer}
/>
