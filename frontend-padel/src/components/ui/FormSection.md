// src/components/ui/FormSection.md

# FormSection

Componente reutilizable para estructurar bloques de formularios, configuraciones o secciones visuales con título, descripción e ícono opcional. Centraliza paddings, layout responsivo y aplica tokens visuales desde el tema.

---

## ✅ Props

| Prop         | Tipo       | Descripción                                                    |
|--------------|------------|----------------------------------------------------------------|
| `title`      | `string`   | Título principal de la sección                                 |
| `description`| `string?`  | Texto auxiliar opcional debajo del título                      |
| `children`   | `ReactNode`| Contenido renderizado dentro de la sección (inputs, botones...)|
| `icon`       | `JSX?`     | Ícono opcional a la izquierda del título                       |

---

## 🧱 Ejemplo de uso

```jsx
// src/components/ui/FormSection.jsx

<FormSection
  title="Configuración de Pago"
  description="Completa los datos requeridos para activar la reserva automatizada."
  icon={<FiSettings />}
>
  <Input placeholder="Destinatario" ... />
  <Input placeholder="CBU" ... />
  <Button type="submit">Guardar</Button>
</FormSection>
