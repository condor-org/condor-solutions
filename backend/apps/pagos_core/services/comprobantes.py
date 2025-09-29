# apps/pagos_core/services/comprobantes.py

import hashlib
import re
from datetime import datetime
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from apps.turnos_core.models import Turno
from PyPDF2 import PdfReader
from io import BytesIO
from PIL import Image
import pytesseract
import logging
from apps.turnos_padel.models import AbonoMes
from apps.pagos_core.models import ComprobantePago, PagoIntento, ComprobanteAbono

from django.contrib.contenttypes.models import ContentType
from apps.turnos_core.models import Prestador

from django.db import transaction

logger = logging.getLogger(__name__)

try:
    import dateutil.parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False

import os
import tempfile
from django.core.exceptions import ValidationError
from . import ocr_providers as gcv


# --- NUEVOS IMPORTS (agregar cerca de los demás) ---
from apps.pagos_core.services.comprobante_parser import registry
from apps.pagos_core.services.comprobante_parser import generic as generic_extractor
from apps.pagos_core.services.comprobante_parser.base import ExtractionError as ParserExtractionError


ANTIGUEDAD_MAXIMA_DE_COMPROBANTE_EN_MINUTOS = 15


class ComprobanteService:

    @staticmethod
    def download_comprobante(comprobante_id: int, usuario) -> ComprobantePago:
        try:
            comprobante = ComprobantePago.objects.get(pk=comprobante_id)
        except ComprobantePago.DoesNotExist:
            raise PermissionDenied("Comprobante no encontrado.")

        if not comprobante.archivo:
            raise PermissionDenied("El comprobante no tiene archivo asociado.")

        if usuario.is_authenticated and usuario.tipo_usuario == "super_admin":
            return comprobante

        if usuario.is_authenticated and usuario.tipo_usuario == "admin_cliente":
            if comprobante.cliente == usuario.cliente:
                return comprobante

        if comprobante.turno and comprobante.turno.usuario == usuario:
            return comprobante

        raise PermissionDenied("No tenés permiso para ver este comprobante.")

    @staticmethod
    def _generate_hash(file_obj) -> str:
        hasher = hashlib.sha256()
        for chunk in file_obj.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    @transaction.atomic
    def validar_y_crear_comprobante_abono(cls, abono, file_obj, usuario, monto_esperado: float):
        """
        Valida el comprobante contra alias/CBU de la sede y el monto_esperado (restante).
        Crea ComprobanteAbono y un PagoIntento. No modifica turnos ni bonificaciones.
        """
        if not file_obj:
            raise ValidationError("Debés subir comprobante.")

        # hash para evitar duplicados
        checksum = cls._generate_hash(file_obj)
        if ComprobanteAbono.objects.filter(hash_archivo=checksum).exists():
            raise ValidationError("Comprobante duplicado.")

        # Datos de la sede (alias/cbu)
        alias = abono.tipo_clase.configuracion_sede.alias
        cbu_cvu = abono.tipo_clase.configuracion_sede.cbu_cvu
        if not (alias or cbu_cvu):
            raise ValidationError("Alias/CBU no configurados para la sede.")

        config_data = {
            "cbu": cbu_cvu,
            "alias": alias,
            "monto_esperado": float(monto_esperado),
            "tiempo_maximo_minutos": ANTIGUEDAD_MAXIMA_DE_COMPROBANTE_EN_MINUTOS,
        }

        # Validación OCR/parseo
        datos = cls._parse_and_validate(file_obj, config_data)

        # Crear o obtener ComprobanteAbono existente
        comprobante, created = ComprobanteAbono.objects.get_or_create(
            abono_mes=abono,
            defaults={
                'cliente': usuario.cliente,
                'archivo': file_obj,
                'hash_archivo': checksum,
                'datos_extraidos': datos,
            }
        )
        
        # Si ya existía, actualizar con los nuevos datos
        if not created:
            comprobante.cliente = usuario.cliente
            comprobante.archivo = file_obj
            comprobante.hash_archivo = checksum
            comprobante.datos_extraidos = datos
            comprobante.save()

        # Intento de pago
        alias_dest = datos.get("alias") or (f"Usando CBU/CVU {datos.get('cbu_destino')}" if datos.get("cbu_destino") else "")
        cbu_dest = datos.get("cbu_destino") or (f"Usando alias {datos.get('alias')}" if datos.get("alias") else "")
        PagoIntento.objects.create(
            cliente=usuario.cliente,
            usuario=usuario,
            estado="pre_aprobado",
            monto_esperado=datos.get("monto", float(monto_esperado)),
            moneda="ARS",
            alias_destino=alias_dest,
            cbu_destino=cbu_dest,
            origen=comprobante,
            tiempo_expiracion=timezone.now() + timezone.timedelta(minutes=config_data["tiempo_maximo_minutos"]),
        )

        return comprobante

    @staticmethod
    def _extract_text(file_obj) -> str:
        """
        Extrae texto con Google Cloud Vision (ocr_providers).
        - PDF: se vuelca a un archivo temporal y se pasa la ruta (GCV async vía GCS).
        - Imagen: se pasa el file-like directamente (bytes).
        Siempre resetea el puntero del archivo al final.
        """
        name = getattr(file_obj, "name", "") or ""
        ext = (name.rsplit(".", 1)[-1] if "." in name else "").lower()

        def _seek0():
            try:
                file_obj.seek(0)
            except Exception:
                pass

        try:
            if ext == "pdf":
                # Guardar a /tmp para pasarlo como ruta a Vision
                _seek0()
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    if hasattr(file_obj, "chunks"):
                        for chunk in file_obj.chunks():
                            tmp.write(chunk)
                    else:
                        tmp.write(file_obj.read())
                    tmp_path = tmp.name

                meta = gcv.extract_text(tmp_path)  # {'texto', 'avg_confidence', ...}
                texto = meta.get("texto") or ""

                # limpieza temporal
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            else:
                # Imagen (jpg/png/webp/etc.) → Vision por bytes
                _seek0()
                meta = gcv.extract_text(file_obj)
                texto = meta.get("texto") or ""

            # Log + chequeo de confianza (no bloqueante, solo warning)
            avg = float(meta.get("avg_confidence") or 0.0)
            weird = meta.get("suspicious_tokens") or []
            logger.debug(
                "OCR Vision: engine=%s | avg_conf=%.3f | weird_tokens=%d",
                meta.get("engine"), avg, len(weird)
            )
            if not gcv.is_trustable(meta):
                logger.warning(
                    "OCR de baja confianza (avg=%.3f, sospechosas=%d). Sigo con el parseo.",
                    avg, len(weird)
                )

            return texto

        except Exception as e:
            logger.exception("Fallo en OCR con Google Vision: %s", e)
            raise ValidationError("No se pudo leer el comprobante. Probá con otra captura/archivo.")
        finally:
            _seek0()

    @staticmethod
    def _parse_and_validate(file_obj, config) -> dict:
        """
        Reglas de negocio (se mantienen):
        - La fecha se EXTRAE del texto y debe ser del DÍA de hoy (ignora hora).
        - El monto debe coincidir con el monto oficial esperado.
        - El destino (CBU/Alias) debe matchear lo configurado para la sede (si aplica).
        """
        texto = ComprobanteService._extract_text(file_obj)

        # Config normalizada (acepta dict o modelo)
        cbu_cfg = getattr(config, "cbu", None) or (isinstance(config, dict) and config.get("cbu"))
        alias_cfg = getattr(config, "alias", None) or (isinstance(config, dict) and config.get("alias"))
        monto_esperado = getattr(config, "monto_esperado", None) or (isinstance(config, dict) and config.get("monto_esperado"))
        tiempo_max = getattr(config, "tiempo_maximo_minutos", None) or (isinstance(config, dict) and config.get("tiempo_maximo_minutos"))

        try:
            monto_esperado = float(monto_esperado)
        except Exception:
            raise ValidationError("Monto esperado inválido en configuración.")

        # La regla de fecha del negocio: HOY (zona local)
        hoy = timezone.localdate()
        cfg = {
            "monto": monto_esperado,
            "fecha": hoy.isoformat(),   # validación exacta por día
        }
        if cbu_cfg:
            cfg["cbu"] = re.sub(r"\D", "", str(cbu_cfg))  # normalizamos CBU a 22 dígitos
        if alias_cfg:
            cfg["alias"] = str(alias_cfg).strip()

        # Elegir extractor por banco o fallback genérico
        extractor = registry.find_extractor(texto) or generic_extractor
        extractor_name = getattr(extractor, "__name__", "generic")

        logger.debug(
            "[comprobantes.parse] Config usada → extractor=%s | monto_esp=%.2f | fecha_esp=%s | cbu_cfg=%s | alias_cfg=%s",
            extractor_name, monto_esperado, hoy.isoformat(), cbu_cfg, alias_cfg
        )

        try:
            parsed = extractor.extract(texto, cfg=cfg)  # dict: monto, fecha, cbu, alias (validados)
            logger.debug("[comprobantes.parse][%s] Parsed bruto: %s", extractor_name, parsed)
        except ParserExtractionError as e:
            logger.warning("[comprobantes.parse][%s] Fallo de extracción/validación: %s", extractor_name, e)
            logger.info("[comprobantes.parse] Fallback → extractor genérico (bank=%s)", extractor_name)
            parsed = generic_extractor.extract(texto, cfg=cfg)
        except Exception as e:
            logger.exception("[comprobantes.parse][%s] Error no manejado en extractor", extractor_name)
            raise ValidationError("No se pudo interpretar el comprobante. Probá con otra captura/archivo.") from e

        # Validaciones defensivas sobre parsed
        fecha_iso = parsed.get("fecha")
        if not fecha_iso:
            logger.error("[comprobantes.parse][%s] Extractor devolvió fecha vacía: %s", extractor_name, parsed)
            raise ValidationError("fecha inválida.")
        monto_detectado = parsed.get("monto")
        if monto_detectado is None:
            logger.error("[comprobantes.parse][%s] Extractor devolvió monto vacío: %s", extractor_name, parsed)
            raise ValidationError("monto inválido.")

        cbu_detectado = parsed.get("cbu")
        alias_detectado = parsed.get("alias")

        logger.debug(
            "[comprobantes.parse][%s] Normalizados → fecha=%s | monto=%s | cbu=%s | alias=%s",
            extractor_name, fecha_iso, monto_detectado, cbu_detectado, alias_detectado
        )

        # Guardamos con hora 00:00 local (mismo comportamiento previo)
        fecha_dt = timezone.make_aware(
            datetime(int(fecha_iso[0:4]), int(fecha_iso[5:7]), int(fecha_iso[8:10]), 0, 0, 0)
        )

        out = {
            "fecha_detectada": fecha_dt.isoformat(),
            "monto": float(monto_detectado or 0.0),
            "cbu_destino": cbu_detectado,
            "alias": alias_detectado,
            "nombre_destinatario": None,   # reservado para futuros extractores específicos
            "nro_referencia": None,        # idem
        }

        logger.info(
            "[comprobantes.parse][ok] extractor=%s fecha=%s monto=%.2f cbu=%s alias=%s",
            extractor_name, out["fecha_detectada"], out["monto"], out["cbu_destino"], out["alias"]
        )
        return out

    @classmethod
    @transaction.atomic
    def upload_comprobante(
        cls,
        turno_id: int,
        tipo_clase_id: int,   # para derivar alias/CBU/monto desde la sede
        file_obj,
        usuario,
        cliente=None,
        ip_cliente=None,
        user_agent=None,
    ) -> ComprobantePago:
        # 0) Archivo
        max_mb = 200
        if file_obj.size > max_mb * 1024 * 1024:
            raise ValidationError(f"El archivo supera el tamaño máximo de {max_mb} MB")
        allowed_exts = {"pdf", "png", "jpg", "jpeg", "bmp", "webp"}
        ext = file_obj.name.rsplit(".", 1)[-1].lower()
        if ext not in allowed_exts:
            allowed = ", ".join(sorted(allowed_exts))
            raise ValidationError(f"Extensión no permitida: «{ext}». Solo se permiten: {allowed}")

        # 1) Turno + permisos
        try:
            turno = Turno.objects.select_related("usuario", "lugar").get(pk=turno_id)
        except Turno.DoesNotExist:
            raise ValidationError("Turno no existe.")
        if turno.content_type != ContentType.objects.get_for_model(Prestador):
            raise ValidationError("El turno no está asociado a un prestador válido.")
        prestador = turno.recurso
        if prestador.cliente_id != (cliente or usuario.cliente).id:
            raise PermissionDenied("No tenés acceso a este turno.")
        tipo_usuario = getattr(usuario, "tipo_usuario", None)
        if tipo_usuario == "admin_cliente":
            if prestador.cliente_id != usuario.cliente.id:
                raise PermissionDenied("No tenés permiso para operar sobre este turno.")
        elif tipo_usuario != "super_admin":
            if turno.usuario_id is not None and turno.usuario_id != usuario.id:
                raise PermissionDenied("No tenés permiso para modificar este turno.")

        # 2) Tipo de clase (sede + precio oficial)
        from apps.turnos_padel.models import TipoClasePadel
        try:
            tipo_clase = TipoClasePadel.objects.select_related(
                "configuracion_sede", "configuracion_sede__sede"
            ).get(pk=tipo_clase_id)
        except TipoClasePadel.DoesNotExist:
            raise ValidationError("Tipo de clase no existe.")
        sede_tipo = getattr(tipo_clase.configuracion_sede, "sede", None)
        if turno.lugar_id and sede_tipo and turno.lugar_id != sede_tipo.id:
            raise ValidationError("El tipo de clase no corresponde a la sede del turno.")

        alias_cfg = getattr(tipo_clase.configuracion_sede, "alias", None)
        cbu_cfg = getattr(tipo_clase.configuracion_sede, "cbu_cvu", None)
        monto_oficial = float(getattr(tipo_clase, "precio", 0) or 0)

        # 3) Anti-duplicado por hash
        file_obj.seek(0)
        checksum = cls._generate_hash(file_obj)
        if ComprobantePago.objects.filter(hash_archivo=checksum).exists():
            raise ValidationError("Comprobante duplicado.")

        # 4) OCR / validaciones
        config_data = {
            "cbu": cbu_cfg,
            "alias": alias_cfg,
            "monto_esperado": monto_oficial,  # referencia autoritativa para el intento
            "tiempo_maximo_minutos": ANTIGUEDAD_MAXIMA_DE_COMPROBANTE_EN_MINUTOS,
        }
        logger.debug(
            "[upload_comprobante.turno] Validando OCR → CBU:%s | Alias:%s | MontoEsp:%s",
            cbu_cfg, alias_cfg, monto_oficial
        )
        try:
            datos = cls._parse_and_validate(file_obj, config_data)
        except:
            raise ValidationError("No se pudo validar el comprobante")

        # 5) Persistir comprobante (NO tocar Turno acá)
        comprobante = ComprobantePago.objects.create(
            turno=turno,
            archivo=file_obj,
            hash_archivo=checksum,
            datos_extraidos=datos,
            cliente=cliente or usuario.cliente,
        )

        # 6) Crear PagoIntento (pre_aprobado) con datos de sede / OCR
        alias_dest = datos.get("alias") or alias_cfg
        cbu_dest = datos.get("cbu_destino") or cbu_cfg
        if not alias_dest and cbu_dest:
            alias_dest = f"Usando CBU/CVU {cbu_dest}"
        if not cbu_dest and alias_dest:
            cbu_dest = f"Usando alias {alias_dest}"

        PagoIntento.objects.create(
            cliente=comprobante.cliente,
            usuario=usuario,
            estado="pre_aprobado",
            monto_esperado=monto_oficial,   # precio oficial, no el OCR
            moneda="ARS",
            alias_destino=alias_dest,
            cbu_destino=cbu_dest,
            origen=comprobante,
            tiempo_expiracion=timezone.now() + timezone.timedelta(
                minutes=ANTIGUEDAD_MAXIMA_DE_COMPROBANTE_EN_MINUTOS
            ),
        )

        logger.info(
            "[turno.comprobante][ok] comp_id=%s turno=%s monto=%s alias=%s cbu=%s",
            comprobante.id, turno.id, monto_oficial, alias_cfg, cbu_cfg
        )
        return comprobante
