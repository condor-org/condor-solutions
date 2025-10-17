# backend/apps/auth_core/utils.py
"""
Utilidades para el sistema multi-tenant.
Helper functions para extraer información de roles desde JWTs.
"""
import jwt
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def get_rol_actual_del_jwt(request):
    """
    Extrae el rol actual del JWT del request.
    Retorna el rol activo o None si no se puede extraer.
    """
    try:
        # Extraer el token del header Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header.split(' ')[1]
        
        # Decodificar el JWT para obtener rol_en_cliente
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        rol_actual = payload.get('rol_en_cliente')
        
        logger.debug(f"[get_rol_actual_del_jwt] Rol extraído: {rol_actual}")
        return rol_actual
        
    except jwt.ExpiredSignatureError:
        logger.warning(f"[get_rol_actual_del_jwt] Token expirado")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"[get_rol_actual_del_jwt] Token inválido: {e}")
        return None
    except Exception as e:
        logger.error(f"[get_rol_actual_del_jwt] Error inesperado: {e}")
        return None
