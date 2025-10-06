# apps/common/management/commands/verificar_memoria.py

import os
import psutil
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Verifica el uso de memoria del sistema y alerta si está cerca del límite"

    def add_arguments(self, parser):
        parser.add_argument(
            "--umbral",
            type=int,
            default=80,
            help="Umbral de alerta en porcentaje (default: 80%)"
        )
        parser.add_argument(
            "--alertar",
            action="store_true",
            help="Enviar alerta si se supera el umbral"
        )

    def handle(self, *args, **options):
        umbral = options["umbral"]
        alertar = options["alertar"]
        
        # Obtener información de memoria
        memoria = psutil.virtual_memory()
        disco = psutil.disk_usage('/')
        
        # Calcular porcentajes
        memoria_porcentaje = memoria.percent
        disco_porcentaje = (disco.used / disco.total) * 100
        
        # Información detallada
        memoria_gb = memoria.total / (1024**3)
        memoria_usada_gb = memoria.used / (1024**3)
        memoria_libre_gb = memoria.available / (1024**3)
        
        disco_gb = disco.total / (1024**3)
        disco_usado_gb = disco.used / (1024**3)
        disco_libre_gb = disco.free / (1024**3)
        
        # Mostrar información
        self.stdout.write(
            self.style.SUCCESS(
                f"📊 MONITOREO DE RECURSOS - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"💾 MEMORIA:\n"
                f"   Total: {memoria_gb:.1f} GB\n"
                f"   Usada: {memoria_usada_gb:.1f} GB ({memoria_porcentaje:.1f}%)\n"
                f"   Libre: {memoria_libre_gb:.1f} GB\n"
                f"💿 DISCO:\n"
                f"   Total: {disco_gb:.1f} GB\n"
                f"   Usado: {disco_usado_gb:.1f} GB ({disco_porcentaje:.1f}%)\n"
                f"   Libre: {disco_libre_gb:.1f} GB"
            )
        )
        
        # Verificar umbrales
        alertas = []
        
        if memoria_porcentaje >= umbral:
            alertas.append(f"⚠️  MEMORIA: {memoria_porcentaje:.1f}% (umbral: {umbral}%)")
            
        if disco_porcentaje >= umbral:
            alertas.append(f"⚠️  DISCO: {disco_porcentaje:.1f}% (umbral: {umbral}%)")
        
        # Mostrar alertas
        if alertas:
            self.stdout.write("\n" + "="*50)
            for alerta in alertas:
                self.stdout.write(self.style.WARNING(alerta))
            
            if alertar:
                self._enviar_alerta(alertas, memoria_porcentaje, disco_porcentaje)
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Todos los recursos están dentro del umbral ({umbral}%)")
            )
        
        # Log para monitoreo
        logger.info(
            f"[MONITOREO] Memoria: {memoria_porcentaje:.1f}%, "
            f"Disco: {disco_porcentaje:.1f}%, "
            f"Alertas: {len(alertas)}"
        )

    def _enviar_alerta(self, alertas, memoria_porcentaje, disco_porcentaje):
        """Envía alerta por email o notificación"""
        try:
            # Aquí puedes implementar envío de email, Slack, etc.
            logger.warning(
                f"[ALERTA_MEMORIA] Recursos críticos: "
                f"Memoria {memoria_porcentaje:.1f}%, Disco {disco_porcentaje:.1f}%"
            )
            
            self.stdout.write(
                self.style.ERROR(
                    f"\n🚨 ALERTA ENVIADA: {len(alertas)} recursos críticos detectados"
                )
            )
        except Exception as e:
            logger.error(f"[ALERTA_MEMORIA] Error enviando alerta: {str(e)}")
