# apps/common/views.py

import psutil
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone

logger = logging.getLogger(__name__)


class MonitoreoRecursosView(APIView):
    """
    🔹 Endpoint para monitorear recursos del servidor (memoria, disco, CPU).
    - Solo accesible por super_admin.
    - Retorna información detallada de recursos del sistema.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Verificar permisos
            if not hasattr(request.user, 'tipo_usuario') or request.user.tipo_usuario != 'super_admin':
                return Response({"error": "Acceso denegado"}, status=403)

            # Obtener información del sistema
            memoria = psutil.virtual_memory()
            disco = psutil.disk_usage('/')
            cpu = psutil.cpu_percent(interval=1)
            
            # Calcular métricas
            memoria_gb = memoria.total / (1024**3)
            memoria_usada_gb = memoria.used / (1024**3)
            memoria_libre_gb = memoria.available / (1024**3)
            
            disco_gb = disco.total / (1024**3)
            disco_usado_gb = disco.used / (1024**3)
            disco_libre_gb = disco.free / (1024**3)
            
            # Determinar estado
            estado_memoria = "ok"
            if memoria.percent >= 90:
                estado_memoria = "critico"
            elif memoria.percent >= 80:
                estado_memoria = "advertencia"
            
            estado_disco = "ok"
            if disco.percent >= 90:
                estado_disco = "critico"
            elif disco.percent >= 80:
                estado_disco = "advertencia"
            
            estado_cpu = "ok"
            if cpu >= 90:
                estado_cpu = "critico"
            elif cpu >= 80:
                estado_cpu = "advertencia"
            
            # Respuesta
            data = {
                "timestamp": timezone.now().isoformat(),
                "memoria": {
                    "total_gb": round(memoria_gb, 2),
                    "usada_gb": round(memoria_usada_gb, 2),
                    "libre_gb": round(memoria_libre_gb, 2),
                    "porcentaje": round(memoria.percent, 1),
                    "estado": estado_memoria
                },
                "disco": {
                    "total_gb": round(disco_gb, 2),
                    "usado_gb": round(disco_usado_gb, 2),
                    "libre_gb": round(disco_libre_gb, 2),
                    "porcentaje": round(disco.percent, 1),
                    "estado": estado_disco
                },
                "cpu": {
                    "porcentaje": round(cpu, 1),
                    "estado": estado_cpu
                },
                "alertas": []
            }
            
            # Agregar alertas si es necesario
            if estado_memoria != "ok":
                data["alertas"].append(f"Memoria: {memoria.percent:.1f}% ({estado_memoria})")
            
            if estado_disco != "ok":
                data["alertas"].append(f"Disco: {disco.percent:.1f}% ({estado_disco})")
            
            if estado_cpu != "ok":
                data["alertas"].append(f"CPU: {cpu:.1f}% ({estado_cpu})")
            
            # Log para monitoreo
            logger.info(
                f"[MONITOREO_API] Memoria: {memoria.percent:.1f}%, "
                f"Disco: {disco.percent:.1f}%, CPU: {cpu:.1f}%"
            )
            
            return Response(data, status=200)
            
        except Exception as e:
            logger.error(f"[MONITOREO_API] Error: {str(e)}")
            return Response({"error": "Error obteniendo información del sistema"}, status=500)
