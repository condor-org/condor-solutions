# Configuración OAuth Compartido - Google Console

Este documento describe cómo configurar OAuth compartido en Google Console para el sistema multi-tenant Condor.

## Objetivo

Configurar un **único Client ID de Google OAuth** que funcione para todos los clientes del sistema, simplificando la gestión y permitiendo automatización.

## Configuración en Google Console

### 1. Acceder a Google Console
1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Seleccionar el proyecto correspondiente
3. Navegar a **APIs & Services** > **Credentials**

### 2. Crear/Configurar OAuth Client
1. **Crear nuevo OAuth Client** o editar existente
2. **Tipo**: Web application
3. **Nombre**: `Condor Multi-Tenant System`

### 3. Configurar Authorized Redirect URIs

#### Para Desarrollo (Dev)
```
https://lob-padel-dev.cnd-ia.com/oauth/google/callback
https://distrito-padel-dev.cnd-ia.com/oauth/google/callback
https://canchas-dev.cnd-ia.com/oauth/google/callback
https://medicina-dev.cnd-ia.com/oauth/google/callback
https://superadmin-dev.cnd-ia.com/oauth/google/callback
```

#### Para Producción (Prod)
```
https://lob-padel.cnd-ia.com/oauth/google/callback
https://distrito-padel.cnd-ia.com/oauth/google/callback
https://canchas.cnd-ia.com/oauth/google/callback
https://medicina.cnd-ia.com/oauth/google/callback
https://superadmin.cnd-ia.com/oauth/google/callback
```

#### Wildcards (Recomendado)
Para simplificar la gestión, se pueden usar wildcards:
```
https://*-dev.cnd-ia.com/oauth/google/callback
https://*.cnd-ia.com/oauth/google/callback
```

**Nota**: Google no soporta wildcards directamente, pero se pueden agregar dominios específicos.

### 4. Configurar Authorized JavaScript Origins

#### Para Desarrollo
```
https://lob-padel-dev.cnd-ia.com
https://distrito-padel-dev.cnd-ia.com
https://canchas-dev.cnd-ia.com
https://medicina-dev.cnd-ia.com
https://superadmin-dev.cnd-ia.com
```

#### Para Producción
```
https://lob-padel.cnd-ia.com
https://distrito-padel.cnd-ia.com
https://canchas.cnd-ia.com
https://medicina.cnd-ia.com
https://superadmin.cnd-ia.com
```

## Variables de Entorno

### Archivo `.env.dev`
```bash
# OAuth Compartido
PUBLIC_GOOGLE_CLIENT_ID=tu_client_id_aqui
PUBLIC_OAUTH_REDIRECT_URI=https://hostname/oauth/google/callback
```

### Archivo `.env.prod`
```bash
# OAuth Compartido
PUBLIC_GOOGLE_CLIENT_ID=tu_client_id_aqui
PUBLIC_OAUTH_REDIRECT_URI=https://hostname/oauth/google/callback
```

## Configuración Dinámica

### En el Frontend
El frontend determina dinámicamente el `redirect_uri` basado en el hostname actual:

```javascript
// En shared-auth/oauthClient.js
const redirectUri = `${window.location.origin}/oauth/google/callback`;
```

### En el Backend
El backend maneja el callback OAuth y redirige al frontend correcto:

```python
# En apps/auth_core/views.py
def oauth_callback(request):
    # Procesar OAuth
    # Redirigir al frontend correcto basado en el hostname
    return redirect(f"https://{hostname}/")
```

## Ventajas del OAuth Compartido

### ✅ Ventajas
- **Simplicidad**: Un solo Client ID para gestionar
- **Automatización**: Fácil agregar nuevos clientes
- **Consistencia**: Misma experiencia de autenticación
- **Mantenimiento**: Menos configuración en Google Console

### ⚠️ Consideraciones
- **Seguridad**: Todos los clientes comparten el mismo Client ID
- **Límites**: Google tiene límites en el número de redirect URIs
- **Debugging**: Más difícil debuggear problemas específicos

## Automatización

### Script para Agregar Nuevo Cliente
```bash
#!/bin/bash
# add-client-oauth.sh

CLIENT_NAME=$1
DOMAIN=$2

# Agregar redirect URI a Google Console (manual por ahora)
echo "Agregar manualmente a Google Console:"
echo "https://${CLIENT_NAME}-dev.cnd-ia.com/oauth/google/callback"
echo "https://${CLIENT_NAME}.cnd-ia.com/oauth/google/callback"

# Crear cliente en base de datos
python manage.py create_client \
  --name="$CLIENT_NAME" \
  --domain="$DOMAIN" \
  --tipo_fe="padel"
```

### API para Gestión de OAuth
```python
# Endpoint para obtener configuración OAuth
@api_view(['GET'])
def oauth_config(request):
    return JsonResponse({
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': f"https://{request.META['HTTP_HOST']}/oauth/google/callback"
    })
```

## Testing

### 1. Probar OAuth en Dev
```bash
# Probar con diferentes hostnames
curl -H "Host: lob-padel-dev.cnd-ia.com" https://dev.cnd-ia.com/api/tenant/config/
curl -H "Host: canchas-dev.cnd-ia.com" https://dev.cnd-ia.com/api/tenant/config/
```

### 2. Probar Callback OAuth
```bash
# Simular callback OAuth
curl -X POST https://dev.cnd-ia.com/api/auth/oauth/callback/ \
  -H "Host: lob-padel-dev.cnd-ia.com" \
  -d "code=test_code&state=test_state"
```

## Próximos Pasos

1. **Configurar Google Console** con redirect URIs
2. **Probar OAuth** en entorno de desarrollo
3. **Implementar automatización** para nuevos clientes
4. **Documentar proceso** de onboarding
5. **Testing** completo del flujo OAuth

## Troubleshooting

### Error: "redirect_uri_mismatch"
- Verificar que el redirect URI esté en Google Console
- Verificar que el hostname sea correcto
- Verificar que no haya trailing slashes

### Error: "invalid_client"
- Verificar que el Client ID sea correcto
- Verificar que el Client ID esté habilitado

### Error: "access_denied"
- Verificar que el usuario tenga permisos
- Verificar que el scope sea correcto
