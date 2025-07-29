# Logging en el Backend

Esta aplicación usa la configuración de `LOGGING` de Django para enviar todos los eventos a la consola. 

## Variables de entorno

- `DJANGO_LOGGING`: si vale `True` se registran eventos normalmente. Si vale `False` se deshabilitan casi todos los logs (nivel `CRITICAL`).
- `DJANGO_LOG_LEVEL`: nivel para el logger raíz (`DEBUG`, `INFO`, `WARNING`, etc.).

## Middleware

Se añadió `condor_core.middleware.LoggingMiddleware` que registra cada petición y respuesta con su método, ruta y código de estado.
