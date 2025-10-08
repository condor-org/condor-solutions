# 🔧 Variables de Entorno - Cliente Distrito Padel

## 📋 Resumen

El archivo `env.distrito-padel.example` es una **plantilla** que contiene todas las variables de entorno necesarias para configurar el nuevo cliente "Distrito Padel". **NO es una variable de entorno en sí**, sino un archivo de configuración que debes copiar y personalizar.

## 🎯 Variables Necesarias

### **1. Variables del Frontend (Runtime Config)**

Estas variables se inyectan en el frontend en **tiempo de ejecución** y controlan la apariencia y configuración del cliente:

```bash
# ===========================================
# CONFIGURACIÓN DEL CLIENTE
# ===========================================
PUBLIC_CLIENTE_ID=2                    # ID del cliente en la base de datos
PUBLIC_NOMBRE_CLIENTE=Distrito Padel   # Nombre que aparece en la interfaz
PUBLIC_COLOR_PRIMARIO=#F44336          # Color principal del tema
PUBLIC_COLOR_SECUNDARIO=#000000        # Color secundario del tema

# ===========================================
# CONFIGURACIÓN OAUTH GOOGLE
# ===========================================
PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id-here
PUBLIC_OAUTH_REDIRECT_URI=https://distrito-padel-dev.cnd-ia.com/oauth/google/callback
```

### **2. Variables del Backend (Ya configuradas)**

Estas variables ya están configuradas en `.env.dev` y no necesitan cambios:

```bash
DJANGO_ENV=dev
DJANGO_SETTINGS_MODULE=condor_core.settings.dev
TENANT_STRICT_HOST=True
TENANT_TRUST_PROXY_HEADERS=True
```

## 🔄 Flujo de Variables de Entorno

### **Paso 1: Docker Compose**
```yaml
# docker-compose-dev.yml
frontend_dev:
  environment:
    PUBLIC_CLIENTE_ID: ${PUBLIC_CLIENTE_ID}
    PUBLIC_NOMBRE_CLIENTE: ${PUBLIC_NOMBRE_CLIENTE}
    PUBLIC_COLOR_PRIMARIO: ${PUBLIC_COLOR_PRIMARIO}
    PUBLIC_COLOR_SECUNDARIO: ${PUBLIC_COLOR_SECUNDARIO}
    PUBLIC_GOOGLE_CLIENT_ID: ${PUBLIC_GOOGLE_CLIENT_ID}
    PUBLIC_OAUTH_REDIRECT_URI: ${PUBLIC_OAUTH_REDIRECT_URI}
```

### **Paso 2: Frontend Entrypoint**
```bash
# frontend-padel/docker/entrypoint.sh
cat >/usr/share/nginx/html/config.js <<EOF
window.RUNTIME_CONFIG = {
  CLIENTE_ID: "${PUBLIC_CLIENTE_ID}",
  NOMBRE_CLIENTE: "${PUBLIC_NOMBRE_CLIENTE}",
  COLOR_PRIMARIO: "${PUBLIC_COLOR_PRIMARIO}",
  COLOR_SECUNDARIO: "${PUBLIC_COLOR_SECUNDARIO}",
  GOOGLE_CLIENT_ID: "${PUBLIC_GOOGLE_CLIENT_ID}",
  OAUTH_REDIRECT_URI: "${PUBLIC_OAUTH_REDIRECT_URI}"
};
EOF
```

### **Paso 3: Frontend App**
```javascript
// frontend-padel/src/config/runtime.js
const rc = window.RUNTIME_CONFIG || {};
export const CLIENTE_ID = String(rc.CLIENTE_ID || '1');
export const NOMBRE_CLIENTE = rc.NOMBRE_CLIENTE || 'Condor';
export const COLOR_PRIMARIO = rc.COLOR_PRIMARIO || '#F44336';
```

## 🚀 Cómo Implementar

### **1. Copiar archivo de plantilla**
```bash
cp scripts/env.distrito-padel.example .env.dev
```

### **2. Editar variables específicas**
```bash
nano .env.dev
```

### **3. Configurar OAuth en Google Console**
- Crear nuevo OAuth Client ID
- Configurar redirect URI: `https://distrito-padel-dev.cnd-ia.com/oauth/google/callback`
- Copiar Client ID a `PUBLIC_GOOGLE_CLIENT_ID`

### **4. Reiniciar servicios**
```bash
docker-compose -f docker-compose-dev.yml down
docker-compose -f docker-compose-dev.yml up -d
```

## 🎨 Efecto en el Frontend

### **Configuración Visual**
- **Nombre**: "Distrito Padel" aparece en la interfaz
- **Colores**: Tema personalizado con colores específicos
- **Logo**: Se puede configurar logo específico del cliente

### **Configuración OAuth**
- **Login**: Usa Google OAuth configurado para el dominio específico
- **Redirect**: Después del login, redirige al dominio correcto

## 🔍 Verificación

### **Verificar Runtime Config**
```javascript
// En el browser, abrir DevTools Console
console.log(window.RUNTIME_CONFIG);
```

### **Verificar Variables de Entorno**
```bash
# En el contenedor del frontend
docker exec frontend_condor_dev env | grep PUBLIC_
```

## 🚨 Troubleshooting

### **Error: "Cliente no encontrado"**
- Verificar que `PUBLIC_CLIENTE_ID` coincide con el ID en la base de datos
- Ejecutar `./scripts/verify-distrito-padel.sh`

### **Error: "OAuth no funciona"**
- Verificar que `PUBLIC_GOOGLE_CLIENT_ID` está configurado
- Verificar que `PUBLIC_OAUTH_REDIRECT_URI` coincide con Google Console
- Verificar que el certificado SSL es válido

### **Error: "Colores no se aplican"**
- Verificar que las variables `PUBLIC_COLOR_*` están configuradas
- Verificar que el frontend se reinició después del cambio
- Verificar que no hay errores en la consola del browser

## 📊 Estructura de Archivos

```
scripts/
├── env.distrito-padel.example    # ← Plantilla de variables
├── bootstrap-distrito-padel.sh  # ← Script de bootstrap
├── verify-distrito-padel.sh     # ← Script de verificación
└── README-distrito-padel.md     # ← Documentación completa
```

## 🎯 Próximos Pasos

1. **Configurar variables de entorno**
2. **Ejecutar bootstrap del cliente**
3. **Configurar OAuth en Google Console**
4. **Probar funcionamiento completo**
5. **Documentar configuración específica**

## 📞 Soporte

Si encuentras problemas:
1. Revisar logs: `docker logs frontend_condor_dev`
2. Verificar configuración: `./scripts/verify-distrito-padel.sh`
3. Revisar variables: `docker exec frontend_condor_dev env | grep PUBLIC_`
4. Contactar al equipo de desarrollo
