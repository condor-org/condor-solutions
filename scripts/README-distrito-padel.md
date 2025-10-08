# 🏢 Configuración Cliente: Distrito Padel

Este documento explica cómo configurar el nuevo cliente "Distrito Padel" en el entorno de desarrollo.

## 📋 Prerrequisitos

- ✅ EC2 de desarrollo configurada
- ✅ DNS configurado en Cloudflare
- ✅ Certificados SSL válidos
- ✅ Acceso a la base de datos de desarrollo

## 🚀 Pasos de Implementación

### 1. Configurar DNS

En Cloudflare, agregar:
```
distrito-padel-dev.cnd-ia.com → IP EC2 Dev
```

### 2. Ejecutar Bootstrap

```bash
# En la EC2 de dev, en el directorio del backend
./scripts/bootstrap-distrito-padel.sh
```

Este script:
- ✅ Crea el cliente "Distrito Padel"
- ✅ Crea el dominio "distrito-padel-dev.cnd-ia.com"
- ✅ Crea el usuario admin
- ✅ Configura sedes y tipos de padel

### 3. Verificar Configuración

```bash
# Verificar que todo está configurado correctamente
./scripts/verify-distrito-padel.sh
```

### 4. Configurar OAuth Google

1. Ir a [Google Console](https://console.developers.google.com/)
2. Crear nuevo OAuth Client ID
3. Configurar:
   - **Authorized origins**: `https://distrito-padel-dev.cnd-ia.com`
   - **Authorized redirect URIs**: `https://distrito-padel-dev.cnd-ia.com/oauth/google/callback`

### 5. Actualizar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp scripts/env.distrito-padel.example .env.dev

# Editar con los valores reales
nano .env.dev
```

Variables importantes:
```bash
PUBLIC_CLIENTE_ID=2
PUBLIC_NOMBRE_CLIENTE=Distrito Padel
PUBLIC_COLOR_PRIMARIO=#F44336
PUBLIC_COLOR_SECUNDARIO=#000000
PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id-here
PUBLIC_OAUTH_REDIRECT_URI=https://distrito-padel-dev.cnd-ia.com/oauth/google/callback
```

### 6. Reiniciar Servicios

```bash
# En la EC2 de dev
docker-compose -f docker-compose-dev.yml down
docker-compose -f docker-compose-dev.yml up -d
```

## 🧪 Testing

### Verificar Funcionamiento

1. **Acceder a la aplicación**:
   ```
   https://distrito-padel-dev.cnd-ia.com
   ```

2. **Verificar tenant resolution**:
   - Debe mostrar "Distrito Padel" en el frontend
   - Debe usar los colores configurados
   - Debe permitir login con OAuth

3. **Verificar aislamiento**:
   - Los datos deben estar aislados por cliente
   - No debe ver datos de otros clientes

## 🔧 Troubleshooting

### Error: "Cliente no encontrado"
```bash
# Verificar que el bootstrap se ejecutó correctamente
./scripts/verify-distrito-padel.sh
```

### Error: "DNS no resuelve"
- Verificar configuración en Cloudflare
- Verificar que el DNS se propagó (puede tomar unos minutos)

### Error: "OAuth no funciona"
- Verificar configuración en Google Console
- Verificar que las URIs coinciden exactamente
- Verificar que el certificado SSL es válido

### Error: "Nginx no reconoce el dominio"
- Verificar que se actualizó `nginx.ec2.dev.conf`
- Verificar que se reiniciaron los servicios
- Verificar logs de nginx: `docker logs reverse-proxy_condor`

## 📊 Estructura de Datos

### Cliente Creado
```sql
-- Cliente
INSERT INTO clientes_core_cliente (
    nombre, tipo_cliente, theme, color_primario, color_secundario
) VALUES (
    'Distrito Padel', 'padel', 'classic', '#F44336', '#000000'
);

-- Dominio
INSERT INTO clientes_core_clientedominio (
    cliente_id, hostname, is_primary, activo
) VALUES (
    2, 'distrito-padel-dev.cnd-ia.com', true, true
);
```

### Usuarios Creados
- **Admin**: `admin@distrito-padel.com` / `admin123`
- **Profesor**: `lucas@lucas.com` / `lucas123`
- **Usuario**: `nacho@nacho.com` / `nacho123`

## 🎯 Próximos Pasos

Una vez que funcione en dev:

1. **Probar funcionalidad completa**
2. **Verificar aislamiento de datos**
3. **Documentar configuración específica**
4. **Preparar para producción**

## 📞 Soporte

Si encuentras problemas:
1. Revisar logs: `docker logs backend_condor_dev`
2. Verificar configuración: `./scripts/verify-distrito-padel.sh`
3. Revisar este README
4. Contactar al equipo de desarrollo
