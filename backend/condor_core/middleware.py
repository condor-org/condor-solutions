# backend/condor_core/middleware.py
import logging
import jwt
from django.conf import settings

logger = logging.getLogger(__name__)

class RolMiddleware:
    """
    Middleware que extrae el rol actual del JWT y lo pone en request.rol_actual
    para que las vistas puedan usarlo sin tener que decodificar el JWT.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Inicializar rol_actual como None
        request.rol_actual = None
        
        logger.info(f"[RolMiddleware] Procesando request: {request.path}")
        
        # Solo procesar si el usuario está autenticado
        if hasattr(request, 'user') and request.user.is_authenticated:
            logger.info(f"[RolMiddleware] Usuario autenticado: {request.user.email}")
            try:
                # Extraer el token del header Authorization
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                logger.info(f"[RolMiddleware] Auth header: {auth_header[:50]}...")
                
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                    logger.info(f"[RolMiddleware] Token extraído: {token[:50]}...")
                    
                    # Decodificar el JWT para obtener rol_en_cliente
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                    rol_actual = payload.get('rol_en_cliente')
                    
                    # Agregar el rol a request para que las vistas lo usen
                    request.rol_actual = rol_actual
                    
                    logger.info(f"[RolMiddleware] Rol extraído: {rol_actual} para usuario {request.user.email}")
                else:
                    logger.warning(f"[RolMiddleware] No hay Bearer token en header")
                    
            except jwt.ExpiredSignatureError:
                logger.warning(f"[RolMiddleware] Token expirado para usuario {request.user.email}")
            except jwt.InvalidTokenError as e:
                logger.warning(f"[RolMiddleware] Token inválido: {e}")
            except Exception as e:
                logger.error(f"[RolMiddleware] Error inesperado: {e}")

        # Continuar con el siguiente middleware/vista
        return self.get_response(request)