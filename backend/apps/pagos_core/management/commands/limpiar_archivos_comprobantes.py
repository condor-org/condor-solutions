# apps/pagos_core/management/commands/limpiar_archivos_comprobantes.py

import os
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.pagos_core.models import ComprobantePago, ComprobanteAbono

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Limpia archivos de comprobantes antiguos del sistema de archivos.\n"
        "Por defecto ejecuta en modo dry-run (no borra archivos reales)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=30,
            help="Días de retención (default: 30). Archivos más antiguos se borran."
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Ejecutar borrado real (sin este flag solo muestra qué borraría)"
        )
        parser.add_argument(
            "--cliente-id",
            type=int,
            default=None,
            help="Limitar limpieza a un cliente específico (opcional)"
        )
        parser.add_argument(
            "--tipo",
            type=str,
            choices=["pagos", "abonos", "todos"],
            default="todos",
            help="Tipo de comprobantes a limpiar (default: todos)"
        )

    def handle(self, *args, **options):
        dias = options["dias"]
        apply = options["apply"]
        cliente_id = options["cliente_id"]
        tipo = options["tipo"]
        
        fecha_limite = timezone.now() - timedelta(days=dias)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"🧹 Limpieza de archivos de comprobantes\n"
                f"📅 Fecha límite: {fecha_limite.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🔧 Modo: {'REAL' if apply else 'DRY-RUN'}\n"
                f"👤 Cliente: {cliente_id or 'Todos'}\n"
                f"📄 Tipo: {tipo}\n"
            )
        )

        stats = {
            "comprobantes_pago": {"encontrados": 0, "archivos_borrados": 0, "errores": 0},
            "comprobantes_abono": {"encontrados": 0, "archivos_borrados": 0, "errores": 0},
            "archivos_huérfanos": {"encontrados": 0, "borrados": 0, "errores": 0}
        }

        # Procesar ComprobantePago
        if tipo in ["pagos", "todos"]:
            stats["comprobantes_pago"] = self._limpiar_comprobantes_pago(
                fecha_limite, cliente_id, apply
            )

        # Procesar ComprobanteAbono
        if tipo in ["abonos", "todos"]:
            stats["comprobantes_abono"] = self._limpiar_comprobantes_abono(
                fecha_limite, cliente_id, apply
            )

        # Mostrar resumen
        self._mostrar_resumen(stats, apply)

    def _limpiar_comprobantes_pago(self, fecha_limite, cliente_id, apply):
        """Limpia archivos de ComprobantePago antiguos"""
        stats = {"encontrados": 0, "archivos_borrados": 0, "errores": 0}
        
        queryset = ComprobantePago.objects.filter(created_at__lt=fecha_limite)
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        
        stats["encontrados"] = queryset.count()
        
        for comprobante in queryset:
            try:
                if comprobante.archivo and comprobante.archivo.storage.exists(comprobante.archivo.name):
                    archivo_path = comprobante.archivo.path
                    archivo_size = os.path.getsize(archivo_path) if os.path.exists(archivo_path) else 0
                    
                    if apply:
                        # Borrar archivo del sistema de archivos
                        comprobante.archivo.delete(save=False)
                        # Borrar registro de la BD
                        comprobante.delete()
                        logger.info(
                            f"[LIMPIEZA] Borrado ComprobantePago #{comprobante.id} "
                            f"(cliente: {comprobante.cliente_id}, archivo: {archivo_size} bytes)"
                        )
                    else:
                        logger.info(
                            f"[DRY-RUN] Borraría ComprobantePago #{comprobante.id} "
                            f"(cliente: {comprobante.cliente_id}, archivo: {archivo_size} bytes)"
                        )
                    
                    stats["archivos_borrados"] += 1
                else:
                    # Archivo no existe, borrar registro huérfano
                    if apply:
                        comprobante.delete()
                        logger.info(f"[LIMPIEZA] Borrado registro huérfano ComprobantePago #{comprobante.id}")
                    else:
                        logger.info(f"[DRY-RUN] Borraría registro huérfano ComprobantePago #{comprobante.id}")
                    
                    stats["archivos_borrados"] += 1
                    
            except Exception as e:
                logger.error(f"[ERROR] ComprobantePago #{comprobante.id}: {str(e)}")
                stats["errores"] += 1
        
        return stats

    def _limpiar_comprobantes_abono(self, fecha_limite, cliente_id, apply):
        """Limpia archivos de ComprobanteAbono antiguos"""
        stats = {"encontrados": 0, "archivos_borrados": 0, "errores": 0}
        
        queryset = ComprobanteAbono.objects.filter(created_at__lt=fecha_limite)
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        
        stats["encontrados"] = queryset.count()
        
        for comprobante in queryset:
            try:
                if comprobante.archivo and comprobante.archivo.storage.exists(comprobante.archivo.name):
                    archivo_path = comprobante.archivo.path
                    archivo_size = os.path.getsize(archivo_path) if os.path.exists(archivo_path) else 0
                    
                    if apply:
                        # Borrar archivo del sistema de archivos
                        comprobante.archivo.delete(save=False)
                        # Borrar registro de la BD
                        comprobante.delete()
                        logger.info(
                            f"[LIMPIEZA] Borrado ComprobanteAbono #{comprobante.id} "
                            f"(cliente: {comprobante.cliente_id}, archivo: {archivo_size} bytes)"
                        )
                    else:
                        logger.info(
                            f"[DRY-RUN] Borraría ComprobanteAbono #{comprobante.id} "
                            f"(cliente: {comprobante.cliente_id}, archivo: {archivo_size} bytes)"
                        )
                    
                    stats["archivos_borrados"] += 1
                else:
                    # Archivo no existe, borrar registro huérfano
                    if apply:
                        comprobante.delete()
                        logger.info(f"[LIMPIEZA] Borrado registro huérfano ComprobanteAbono #{comprobante.id}")
                    else:
                        logger.info(f"[DRY-RUN] Borraría registro huérfano ComprobanteAbono #{comprobante.id}")
                    
                    stats["archivos_borrados"] += 1
                    
            except Exception as e:
                logger.error(f"[ERROR] ComprobanteAbono #{comprobante.id}: {str(e)}")
                stats["errores"] += 1
        
        return stats

    def _mostrar_resumen(self, stats, apply):
        """Muestra resumen de la operación"""
        total_encontrados = (
            stats["comprobantes_pago"]["encontrados"] + 
            stats["comprobantes_abono"]["encontrados"]
        )
        total_borrados = (
            stats["comprobantes_pago"]["archivos_borrados"] + 
            stats["comprobantes_abono"]["archivos_borrados"]
        )
        total_errores = (
            stats["comprobantes_pago"]["errores"] + 
            stats["comprobantes_abono"]["errores"]
        )

        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.SUCCESS(
                f"📊 RESUMEN DE LIMPIEZA\n"
                f"🔍 Comprobantes encontrados: {total_encontrados}\n"
                f"🗑️  Archivos {'borrados' if apply else 'que se borrarían'}: {total_borrados}\n"
                f"❌ Errores: {total_errores}\n"
                f"🔧 Modo: {'REAL' if apply else 'DRY-RUN'}"
            )
        )
        
        if not apply and total_borrados > 0:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  Para ejecutar el borrado real, usa: --apply"
                )
            )
        
        self.stdout.write("="*50)
