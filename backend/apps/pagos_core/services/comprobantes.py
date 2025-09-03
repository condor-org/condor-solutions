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

ANTIGUEDAD_MAXIMA_DE_COMPROBANTE_EN_MINUTOS = 150000


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

        # Crear ComprobanteAbono
        comprobante = ComprobanteAbono.objects.create(
            cliente=usuario.cliente,
            abono_mes=abono,
            archivo=file_obj,
            hash_archivo=checksum,
            datos_extraidos=datos,
        )

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
        ext = file_obj.name.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            file_obj.seek(0)
            reader = PdfReader(BytesIO(file_obj.read()))
            texto = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    texto += page_text + "\n"
            file_obj.seek(0)
            logger.debug("Texto extraído (PDF):\n%s\n%s", texto, '-'*40)
            return texto
        elif ext in {"png", "jpg", "jpeg", "bmp", "webp"}:
            file_obj.seek(0)
            img = Image.open(file_obj)
            texto = pytesseract.image_to_string(img)
            file_obj.seek(0)
            logger.debug("Texto extraído (Imagen):\n%s\n%s", texto, '-'*40)
            return texto
        else:
            raise ValidationError(f"Extensión no soportada para extracción de texto: {ext}")

    @staticmethod
    def _extract_monto(texto: str, monto_esperado=None):

        def normalizar_monto(monto_str):
            monto_str = monto_str.strip()

            if '.' in monto_str and ',' in monto_str:
                if monto_str.rfind(',') > monto_str.rfind('.'):
                    monto_str = monto_str.replace('.', '').replace(',', '.')
                else:
                    monto_str = monto_str.replace(',', '')
            elif ',' in monto_str:
                monto_str = monto_str.replace(',', '.')
            elif '.' in monto_str:
                if monto_str.count('.') > 1:
                    monto_str = monto_str.replace('.', '')
                else:
                    if len(monto_str) > 3 and monto_str[-3] == '.' and monto_str[-2:].isdigit():
                        pass  # punto decimal, dejar igual
                    else:
                        monto_str = monto_str.replace('.', '')
            return monto_str

        lineas = texto.lower().split('\n')
        regex_monto = re.compile(r"\$\s*([\d.,]+)")
        palabras_clave = ["importe total", "importe", "monto"]

        # Buscar monto con signo $
        for i, linea in enumerate(lineas):
            if any(palabra in linea for palabra in palabras_clave):
                indices = [i, i + 1, i + 2]
                for idx in indices:
                    if 0 <= idx < len(lineas):
                        match = regex_monto.search(lineas[idx])
                        if match:
                            monto_str = match.group(1)
                            logger.debug("Encontrado monto_str: '%s' en línea: '%s'", monto_str, lineas[idx])
                            monto_str = normalizar_monto(monto_str)
                            logger.debug("Normalizado a: '%s'", monto_str)
                            try:
                                valor = float(monto_str)
                                logger.debug("Monto convertido a float: %s", valor)
                                return valor
                            except ValueError:
                                logger.debug("Error al convertir monto '%s'", monto_str)
                                continue

        # Fallback: buscar números sin signo $ pero con formato de monto (números con puntos y comas)
        regex_num_sin_signo = re.compile(r"([\d.,]{3,})")
        candidatos = []
        for linea in lineas:
            for m in regex_num_sin_signo.findall(linea):
                candidatos.append(m)

        logger.debug("Candidatos a montos sin signo $ encontrados: %s", candidatos)

        for candidato in candidatos:
            monto_str = normalizar_monto(candidato)
            try:
                valor = float(monto_str)
                logger.debug("Monto válido encontrado en fallback: %s", valor)
                # Si monto_esperado está definido, validar que coincida exactamente
                if monto_esperado is not None:
                    if abs(valor - monto_esperado) < 0.001:  # tolerancia muy pequeña para float
                        return valor
                else:
                    return valor
            except ValueError:
                logger.debug("Error al convertir monto en fallback '%s'", monto_str)
                continue

        logger.debug("No se encontró monto válido.")
        return None

    @staticmethod
    def _extract_fecha(texto: str):
        import re
        logger.debug("Iniciando extracción de fecha")

        # 1. Regex para formato numérico clásico dd/mm/yyyy o dd-mm-yyyy o yyyy-mm-dd
        regex_fecha = re.compile(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})")
        match = regex_fecha.search(texto)
        if match:
            fecha_str = match.group(1)
            logger.debug("Fecha encontrada con regex numérico: '%s'", fecha_str)
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                try:
                    fecha = datetime.strptime(fecha_str, fmt)
                    logger.debug("Fecha parseada con formato '%s': %s", fmt, fecha)
                    return fecha
                except ValueError:
                    continue

        # 2. Regex para fechas con mes abreviado en letras (ej: 02/JUL/2025)
        regex_fecha_letras = re.compile(r"(\d{1,2}\/[A-Za-z]{3}\/\d{4})")
        match = regex_fecha_letras.search(texto)
        if match:
            fecha_str = match.group(1)
            logger.debug("Fecha encontrada con regex mes letras: '%s'", fecha_str)
            try:
                fecha = datetime.strptime(fecha_str, "%d/%b/%Y")
                logger.debug("Fecha parseada con mes abreviado: %s", fecha)
                return fecha
            except ValueError as e:
                logger.debug("Error parseando fecha mes letras: %s", e)

        # 3. Regex para fechas tipo "18 de junio de 2025"
        regex_fecha_palabras = re.compile(
            r"(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})",
            re.IGNORECASE
        )
        match_palabras = regex_fecha_palabras.search(texto.lower())
        if match_palabras:
            dia, mes_texto, anio = match_palabras.groups()
            meses = {
                "enero":1, "febrero":2, "marzo":3, "abril":4, "mayo":5, "junio":6,
                "julio":7, "agosto":8, "septiembre":9, "octubre":10, "noviembre":11, "diciembre":12
            }
            mes = meses.get(mes_texto)
            if mes:
                try:
                    fecha = datetime(int(anio), mes, int(dia))
                    logger.debug("Fecha parseada con mes en palabras: %s", fecha)
                    return fecha
                except ValueError:
                    pass

        # 4. Nuevo: Regex para formato ISO con hora: '2025-07-11 17:31:02'
        regex_iso_con_hora = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
        match_iso = regex_iso_con_hora.search(texto)
        if match_iso:
            fecha_str = match_iso.group(1)
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                logger.debug("Fecha parseada con formato ISO y hora: %s", fecha)
                return fecha
            except ValueError as e:
                logger.debug("Error parseando fecha ISO con hora: %s", e)

        # 5. Intentar dateutil parser con fuzzy=True si está disponible
        if HAS_DATEUTIL:
            try:
                fecha = dateutil.parser.parse(texto, fuzzy=True)
                logger.debug("Fecha parseada con dateutil parser: %s", fecha)
                return fecha
            except (ValueError, OverflowError) as e:
                logger.debug("dateutil.parser falló: %s", e)

        logger.debug("No se pudo extraer fecha válida")
        return None

    @staticmethod
    def _extract_cbu_alias_destinatario(texto: str, cbu_esperado: str = None, alias_esperado: str = None):
        alias_regex = re.compile(
            r"alias(?:\s+destinatario)?\s*[:\-]\s*([a-zA-Z0-9.-]{6,22})",
            re.IGNORECASE
        )
        lineas = texto.split('\n')

        logger.debug("Iniciando extracción de CBU/Alias")

        # Buscar cbu_esperado en líneas
        if cbu_esperado:
            logger.debug("Buscando línea por línea CBU esperado: %s", cbu_esperado)
            for i, linea in enumerate(lineas):
                if cbu_esperado in linea:
                    logger.debug("CBU esperado encontrado en línea %s: '%s'", i, linea.strip())
                    return cbu_esperado, None
            logger.debug("CBU esperado NO encontrado en ninguna línea")

        # Buscar alias_esperado en líneas
        if alias_esperado:
            logger.debug("Buscando línea por línea Alias esperado: %s", alias_esperado)
            for i, linea in enumerate(lineas):
                if alias_esperado in linea:
                    logger.debug("Alias esperado encontrado en línea %s: '%s'", i, linea.strip())
                    return None, alias_esperado
            logger.debug("Alias esperado NO encontrado en ninguna línea")

        # Si no se encontró cbu_esperado ni alias_esperado, continuar con búsqueda general (lógica previa)
        alias_dest = None
        cbu_dest = None
        palabras_clave = {
            "para", "destinatario", "del", "cuenta", "cbu", "cvu", "alias",
            "cuenta destino", "cbu destino", "cvú destino", "alias destinatario", "cuenta banco"
        }
        cbu_cvu_regex = re.compile(r"(?<!\d)(\d{22})(?!\d)")

        for i, linea in enumerate(lineas):
            l = linea.lower()
            if any(palabra in l for palabra in palabras_clave):
                alias_en_linea = alias_regex.findall(linea)
                if alias_en_linea:
                    alias_dest = alias_en_linea[0]
                    break
                nums_en_linea = cbu_cvu_regex.findall(linea)
                if nums_en_linea:
                    cbu_dest = nums_en_linea[0]
                    break

        if alias_dest:
            logger.debug("Alias final: %s", alias_dest)
            return None, alias_dest
        if cbu_dest:
            logger.debug("CBU final: %s", cbu_dest)
            return cbu_dest, None

        logger.debug("No se encontró CBU ni alias")
        return None, None


    @staticmethod
    def _parse_and_validate(file_obj, config) -> dict:
        """
        Reglas:
        - La fecha se EXTRAE del texto del comprobante.
        - La validación es estrictamente por DÍA (ignora hora): debe ser igual a timezone.localdate().
        """
        import re
        import unicodedata
        from datetime import datetime

        texto = ComprobanteService._extract_text(file_obj)

        # ===== Helpers locales (robustos y autocontenidos) =====
        _SEP = r"[-/\.]"
        _WS  = r"(?:\s|\u00A0|\u202F|\u2007|\u200B|\u2060)*"

        _MONTH_ABBR = {
            "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
            "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
            "jan": 1, "apr": 4, "aug": 8, "oct": 10, "dec": 12,  # EN extras
        }

        def _month_from_abbr(token: str) -> int | None:
            if not token:
                return None
            return _MONTH_ABBR.get(token.strip().lower()[:3])

        def _normalize_text(s: str) -> str:
            if not s:
                return ""
            s = unicodedata.normalize("NFKC", s)
            # zero-width / joiners
            s = s.replace("\u200B", "").replace("\u2060", "")
            # NBSP variants -> espacio normal
            s = s.replace("\u00A0", " ").replace("\u202F", " ").replace("\u2007", " ")
            # slashes/hyphens “raros” -> ASCII
            s = s.replace("\u2044", "/").replace("\u2215", "/").replace("\uFF0F", "/")
            s = s.replace("\u2010", "-").replace("\u2011", "-").replace("\u2212", "-")
            # colapsa espacios horizontales (dejamos \n)
            s = re.sub(r"[ \t\r\f\v]+", " ", s)
            return s

        def _extract_fecha_solo_dia(texto_: str):
            """
            Devuelve datetime.date o None.
            Prioridades:
              1) dd/mm/yyyy (y variantes con -, .)
              2) yyyy/mm/dd (y variantes)
              3) '18 de junio de 2025'
              4) ISO 'YYYY-MM-DD'
              5) dd/MES_ABREV/yyyy o 'dd MES yyyy' (ES/EN)
              6) dd/mm/yy (al final, con guardia)
              7) Fallback con dateutil (si está)
            """
            s = _normalize_text(texto_ or "")

            # 1) dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy
            m = re.search(fr"(?<!\d)(\d{{1,2}}){_WS}{_SEP}{_WS}(\d{{1,2}}){_WS}{_SEP}{_WS}(\d{{4}})", s)
            if m:
                d, mth, yyyy = map(int, m.groups())
                try:
                    return datetime(yyyy, mth, d).date()
                except ValueError:
                    pass

            # 2) yyyy/mm/dd, yyyy-mm-dd, yyyy.mm.dd
            m = re.search(fr"(?<!\d)(\d{{4}}){_WS}{_SEP}{_WS}(\d{{1,2}}){_WS}{_SEP}{_WS}(\d{{1,2}})", s)
            if m:
                yyyy, mm, dd = map(int, m.groups())
                try:
                    return datetime(yyyy, mm, dd).date()
                except ValueError:
                    pass

            # 3) '18 de junio de 2025'
            m = re.search(r"(?i)(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})", s)
            if m:
                d, mes_texto, yyyy = m.groups()
                meses = {
                    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
                    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
                    "noviembre": 11, "diciembre": 12
                }
                mes = meses.get(mes_texto.lower())
                if mes:
                    try:
                        return datetime(int(yyyy), mes, int(d)).date()
                    except ValueError:
                        pass

            # 4) ISO 'YYYY-MM-DD'
            m = re.search(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})", s)
            if m:
                yyyy, mm, dd = map(int, m.groups())
                try:
                    return datetime(yyyy, mm, dd).date()
                except ValueError:
                    pass

            # 5) dd/MES_ABREV/yyyy o "dd MES yyyy" (ES/EN, may/minus)
            m = re.search(r"(?i)(?<!\d)(\d{1,2})[ /-]([A-Za-z]{3,})[ /-](\d{4})", s)
            if m:
                d_str, mon_token, yyyy_str = m.groups()
                mes = _month_from_abbr(mon_token)
                if mes:
                    try:
                        return datetime(int(yyyy_str), mes, int(d_str)).date()
                    except ValueError:
                        pass

            # 6) dd/mm/yy, dd-mm-yy, dd.mm.yy  (al final, con guardia para no “chupar” 2025)
            m = re.search(fr"(?<!\d)(\d{{1,2}}){_WS}{_SEP}{_WS}(\d{{1,2}}){_WS}{_SEP}{_WS}(\d{{2}})(?!\d)", s)
            if m:
                d, mth, yy = map(int, m.groups())
                try:
                    return datetime(2000 + yy, mth, d).date()
                except ValueError:
                    pass

            # 7) Fallback con dateutil
            if HAS_DATEUTIL:
                try:
                    dt = dateutil.parser.parse(s, fuzzy=True, dayfirst=True)
                    return dt.date()
                except Exception:
                    pass
            return None
        # ===== fin helpers =====

        # 📌 Obtener valores de config (acepta modelo o dict)
        cbu = getattr(config, "cbu", config.get("cbu"))
        alias = getattr(config, "alias", config.get("alias"))
        monto_esperado = getattr(config, "monto_esperado", config.get("monto_esperado"))
        tiempo_max = getattr(config, "tiempo_maximo_minutos", config.get("tiempo_maximo_minutos"))

        try:
            monto_esperado = float(monto_esperado)
        except Exception:
            raise ValidationError("Monto esperado inválido en configuración.")

        # 📌 Extraer monto del comprobante
        monto = ComprobanteService._extract_monto(texto, monto_esperado)
        if monto is None:
            raise ValidationError("No se pudo extraer el monto del comprobante.")

        # 📌 Extraer fecha → comparar SOLO por DÍA con hoy
        fecha_doc = _extract_fecha_solo_dia(texto)
        if fecha_doc is None:
            # fallback al extractor actual y truncar a día
            fecha_dt_tmp = ComprobanteService._extract_fecha(texto)
            if not fecha_dt_tmp:
                raise ValidationError("No se pudo extraer la fecha del comprobante.")
            fecha_doc = fecha_dt_tmp.date()

        hoy = timezone.localdate()
        if fecha_doc != hoy:
            raise ValidationError(
                f"El comprobante tiene fecha inválida: {fecha_doc}. "
                f"Debe ser del día de hoy ({hoy})."
            )

        # Para almacenar/loggear un ISO con tz: 00:00 local del día extraído
        fecha_dt = timezone.make_aware(datetime(fecha_doc.year, fecha_doc.month, fecha_doc.day, 0, 0, 0))

        # 📌 Validar CBU / Alias
        cbu_dest, alias_dest = ComprobanteService._extract_cbu_alias_destinatario(
            texto,
            cbu_esperado=cbu,
            alias_esperado=alias
        )
        if cbu_dest is None and alias_dest is None:
            raise ValidationError("No se pudo extraer CBU o alias del destinatario.")

        # 📌 Validar monto
        if monto < monto_esperado:
            raise ValidationError(f"Monto {monto} menor al esperado {monto_esperado}.")

        # 📌 Validar coincidencia CBU/Alias (si vienen en config)
        if cbu and cbu_dest != cbu:
            if not (alias and alias_dest == alias):
                raise ValidationError(f"CBU {cbu_dest} no coincide con el configurado {cbu}.")
        elif alias and alias_dest != alias and cbu_dest != cbu:
            raise ValidationError(f"Alias {alias_dest} no coincide con el configurado {alias}.")

        return {
            "fecha_detectada": fecha_dt.isoformat(),
            "monto": monto,
            "cbu_destino": cbu_dest,
            "alias": alias_dest,
            "nombre_destinatario": None,
            "nro_referencia": None
        }

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
        datos = cls._parse_and_validate(file_obj, config_data)

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
