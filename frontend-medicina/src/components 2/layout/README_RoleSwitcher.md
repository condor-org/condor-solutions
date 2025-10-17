# Sistema de Selector de Roles

Este sistema permite a los usuarios cambiar entre diferentes vistas según sus roles múltiples en el mismo cliente.

## Componentes

### 1. `RoleSwitcher.jsx`
Selector elegante que aparece en la navbar solo cuando el usuario tiene múltiples roles.

**Características:**
- Solo se muestra si `hasMultipleRoles = true`
- Diseño responsive (mobile/desktop)
- Colores distintivos por rol
- Indicador visual del rol actual
- Menú dropdown con todos los roles disponibles

### 2. `useRoleSwitcher.js`
Hook personalizado que maneja la lógica del cambio de roles.

**Funciones:**
- `selectedRole`: Rol actualmente seleccionado
- `availableRoles`: Array de roles disponibles
- `hasMultipleRoles`: Boolean si tiene múltiples roles
- `changeRole(newRole)`: Cambiar a un rol específico
- `getCurrentRoleInfo()`: Información detallada del rol actual

### 3. `RoleBasedContent.jsx`
Componente de ejemplo que muestra contenido diferente según el rol.

## Uso

### En la Navbar
```jsx
import RoleSwitcher from './RoleSwitcher';

// Se incluye automáticamente en Navbar.jsx
<RoleSwitcher />
```

### En otros componentes
```jsx
import { useRoleSwitcher } from '../../hooks/useRoleSwitcher';

const MyComponent = () => {
  const { selectedRole, changeRole, getCurrentRoleInfo } = useRoleSwitcher();
  const roleInfo = getCurrentRoleInfo();

  if (roleInfo.isAdmin) {
    return <AdminView />;
  }

  if (roleInfo.isCoach) {
    return <CoachView />;
  }

  return <UserView />;
};
```

## Estructura de Datos

### Usuario con múltiples roles:
```json
{
  "cliente_actual": {
    "id": 1,
    "nombre": "Lucas Padel",
    "rol": "admin_cliente",           // Rol principal
    "roles": ["admin_cliente", "coach"], // Todos los roles
    "tipo_cliente": "padel"
  }
}
```

### Información del rol actual:
```javascript
const roleInfo = getCurrentRoleInfo();
// {
//   role: "admin_cliente",
//   isAdmin: true,
//   isManager: false,
//   isCoach: false,
//   isReceptionist: false,
//   isEmployee: false,
//   isUser: false,
//   isSuperAdmin: false
// }
```

## Roles Soportados

| Rol | Label | Color | Descripción |
|-----|-------|-------|-------------|
| `super_admin` | Super Admin | Purple | Acceso total al sistema |
| `admin_cliente` | Admin | Blue | Gestión del cliente |
| `manager` | Manager | Green | Gestión de equipos |
| `coach` | Coach | Orange | Gestión de entrenamientos |
| `receptionist` | Recepcionista | Teal | Atención al cliente |
| `empleado_cliente` | Empleado | Cyan | Funciones operativas |
| `usuario_final` | Usuario | Gray | Acceso básico |

## Implementación de Cambio de Vista

Para implementar el cambio real de vista, modifica el hook `useRoleSwitcher.js`:

```javascript
const changeRole = useCallback((newRole) => {
  if (availableRoles.includes(newRole)) {
    setSelectedRole(newRole);
    
    // Implementar lógica de cambio de vista:
    
    // 1. Cambiar título de la app
    document.title = `App - ${ROLE_LABELS[newRole]}`;
    
    // 2. Mostrar/ocultar elementos del navbar
    // (implementar en Navbar.jsx)
    
    // 3. Cambiar rutas disponibles
    // (implementar en router)
    
    // 4. Actualizar permisos de componentes
    // (implementar en cada componente)
    
    // 5. Guardar preferencia del usuario
    localStorage.setItem('preferred_role', newRole);
  }
}, [availableRoles]);
```

## Responsive Design

- **Mobile**: Selector compacto con iconos
- **Desktop**: Selector completo con labels
- **Tablet**: Adaptación automática

## Accesibilidad

- Soporte para navegación por teclado
- Labels descriptivos
- Indicadores visuales claros
- Contraste adecuado en modo oscuro/claro
