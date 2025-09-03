"""
Extractor robusto para comprobantes del Banco Galicia.

Patrones habituales observados:
- Marca: "Galicia" (a veces con símbolos decorativos al lado)
- Secciones/etiquetas: "Detalle de la operación", "Fecha de operación",
  "Importe", "Datos del destinatario", "Cuenta", "CBU/CVU".
- Leyenda legal frecuente: "Salvo Error u Omisión (S.E.U.O.)"

Estrategia de extracción:
- Fecha: preferencia por la etiqueta "Fecha de operación" y la fecha en las
  líneas inmediatamente siguientes (formato DD/MM/YYYY). Fallback: fecha única global.
- Monto: preferencia por la etiqueta "Importe" y el primer monto cercano
  (líneas siguientes). Fallback: línea limpia con solo monto o único token global.
- CBU destino: dentro del bloque "Datos del destinatario", buscar "Cuenta <22d>"
  o "CBU/CVU <22d>". Fallback: único CBU global.

Reglas de estrictez:
- Si hay múltiples candidatos distintos para un mismo campo, se lanza ExtractionError.
- Si no aparece un campo requerido, también se lanza ExtractionError.

Salida:
- dict(monto: float, fecha: 'YYYY-MM-DD', cbu: str|None, alias: None)

Validación:
- Se compara contra lo esperado con validate_all_expected (monto/fecha/cbu/alias).
"""

from __future__ import annotations
import re
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from ..base import (
    ParseResult, ExtractionError,
    normalize_text_keep_lines, validate_all_expected
)

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────────────
# Detección del banco
# ───────────────────────────────────────────────────────────────────────────────

_GALICIA_PRIMARY = ("galicia",)
_GALICIA_SECONDARY = (
    "detalle de la operación",
    "fecha de operación",
    "s.e.u.o",  # Salvo Error u Omisión
    "datos del destinatario",
)

def matches(texto: str) -> bool:
    """
    Devuelve True si el OCR contiene señales claras de Galicia.
    Requiere la marca primaria ("galicia") y, preferentemente, alguna señal secundaria.
    """
    t = (texto or "").lower()
    if not any(k in t for k in _GALICIA_PRIMARY):
        return False
    # Si falta una secundaria, igual aceptamos si la marca principal está (algunos recibos son muy breves)
    return True


# ───────────────────────────────────────────────────────────────────────────────
# Regex y utilidades específicas
# ───────────────────────────────────────────────────────────────────────────────

# Dinero: admite AR (1.234,56) y US (1,234.56), con o sin símbolo $
_RE_MONEY_TOKEN = re.compile(r"\$?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})")
_RE_MONEY_LINE  = re.compile(r"^\s*\$?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*$", re.MULTILINE)

# Fecha DD/MM/YYYY (o con guiones, por si alguna variante lo usa)
_RE_DATE = re.compile(r"\b([0-3]\d)[/\-]([0-1]\d)[/\-](\d{4})\b")

# Hora opcional (no se usa para devolver, solo como pista si hiciera falta)
_RE_TIME = re.compile(r"\b([0-2]\d):([0-5]\d)(?::([0-5]\d))?\b")

# CBU 22 dígitos
_RE_CBU_22 = re.compile(r"\b(\d{22})\b")
# Etiquetas típicas en Galicia
_RE_TIT_FECHA = re.compile(r"^\s*fecha\s+de\s+operaci[oó]n\s*$", re.IGNORECASE | re.MULTILINE)
_RE_TIT_IMPORTE = re.compile(r"^\s*importe\s*$", re.IGNORECASE | re.MULTILINE)
_RE_TIT_DATOS_DEST = re.compile(r"^\s*datos\s+del\s+destinatario\s*$", re.IGNORECASE | re.MULTILINE)
_RE_LINEA_CUENTA = re.compile(r"^\s*cuenta\s+(\d{22})\s*$", re.IGNORECASE | re.MULTILINE)
_RE_LINEA_CBU_CVU = re.compile(r"^\s*cbu\/cvu\s+(\d{22})\s*$", re.IGNORECASE | re.MULTILINE)

# Ventanas de búsqueda en líneas desde un título
FECHA_WINDOW  = 3   # buscar fecha hasta 3 líneas después de "Fecha de operación"
IMPORTE_WINDOW = 4  # buscar monto hasta 4 líneas después de "Importe"
DEST_WINDOW    = 12 # buscar CBU hasta 12 líneas dentro de "Datos del destinatario"


def _split_lines(text: str) -> List[str]:
    """Devuelve el texto en líneas no vacías, recortadas."""
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]


def _to_float_money(token: str) -> float:
    """
    Convierte un token de dinero a float:
      - Si el último separador es coma, interpretamos formato AR (1.234,56).
      - Si el último separador es punto, interpretamos US (1,234.56).
    """
    s = token.strip()
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")
    if last_comma > last_dot:
        return float(s.replace(".", "").replace(",", "."))
    return float(s.replace(",", ""))


def _iso_from_ddmmyyyy(d: str, m: str, y: str) -> str:
    """Devuelve 'YYYY-MM-DD' validando la fecha."""
    dt = datetime(year=int(y), month=int(m), day=int(d)).date()
    return dt.isoformat()


# ───────────────────────────────────────────────────────────────────────────────
# Extracción: FECHA (preferencia por etiqueta "Fecha de operación")
# ───────────────────────────────────────────────────────────────────────────────

def _extract_fecha_iso(text: str) -> str:
    """
    Preferencia:
      1) Buscar el título "Fecha de operación" y tomar la única fecha en las
         FECHA_WINDOW líneas siguientes.
      2) Fallback: fecha única global en todo el documento.
    Ambigüedad → error.
    """
    lines = _split_lines(text)

    # 1) Ventana desde "Fecha de operación"
    tit_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"fecha\s+de\s+operaci[oó]n", ln, flags=re.IGNORECASE)]
    if tit_idxs:
        candidates = []
        for idx in tit_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + FECHA_WINDOW + 1)])
            for m in _RE_DATE.finditer(window):
                candidates.append(_iso_from_ddmmyyyy(m.group(1), m.group(2), m.group(3)))
        uniq = sorted(set(candidates))
        if len(uniq) == 1:
            return uniq[0]
        if len(uniq) > 1:
            raise ExtractionError(f"Ambigüedad: múltiples fechas cerca de 'Fecha de operación' {uniq}.")

    # 2) Fallback: fecha única global
    all_dates = [_iso_from_ddmmyyyy(m.group(1), m.group(2), m.group(3)) for m in _RE_DATE.finditer(text)]
    if not all_dates:
        raise ExtractionError("No se encontró una fecha válida.")
    uniq_all = sorted(set(all_dates))
    if len(uniq_all) == 1:
        return uniq_all[0]
    raise ExtractionError(f"Ambigüedad: múltiples fechas detectadas {uniq_all}.")


# ───────────────────────────────────────────────────────────────────────────────
# Extracción: MONTO (preferencia por etiqueta "Importe")
# ───────────────────────────────────────────────────────────────────────────────

def _extract_monto(text: str) -> float:
    """
    Preferencia:
      1) Buscar el título "Importe" y tomar el primer monto en las IMPORTE_WINDOW
         líneas siguientes (suele estar en la inmediata).
         - Si hay >1 montos distintos en esa ventana → ambigüedad.
      2) Línea limpia con solo monto.
      3) Único token de dinero global (o el mismo repetido).
    """
    lines = _split_lines(text)

    # 1) Ventana desde "Importe"
    tit_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"importe", ln, flags=re.IGNORECASE)]
    if tit_idxs:
        candidates = []
        for idx in tit_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + IMPORTE_WINDOW + 1)])
            candidates.extend(_RE_MONEY_TOKEN.findall(window))
        if candidates:
            uniq = sorted(set(candidates))
            if len(uniq) == 1:
                return _to_float_money(uniq[0])
            raise ExtractionError("Ambigüedad: múltiples montos distintos cerca de 'Importe'.")

    # 2) Línea limpia
    line_matches = _RE_MONEY_LINE.findall(text)
    if len(line_matches) == 1:
        return _to_float_money(line_matches[0])
    if len(line_matches) > 1:
        raise ExtractionError("Ambigüedad: múltiples líneas con solo un monto.")

    # 3) Tokens globales
    tokens = _RE_MONEY_TOKEN.findall(text)
    if not tokens:
        raise ExtractionError("No se encontró monto en el comprobante.")
    uniq_tokens = sorted(set(tokens))
    if len(uniq_tokens) == 1:
        return _to_float_money(uniq_tokens[0])
    raise ExtractionError(f"Ambigüedad: múltiples montos distintos detectados ({', '.join(uniq_tokens[:3])}).")


# ───────────────────────────────────────────────────────────────────────────────
# Extracción: CBU del destinatario (bloque "Datos del destinatario")
# ───────────────────────────────────────────────────────────────────────────────

def _extract_cbu_destinatario(text: str) -> Optional[str]:
    """
    Preferencia:
      1) Dentro del bloque "Datos del destinatario", aceptar:
         - Línea "Cuenta <22dígitos>"
         - Línea "CBU/CVU <22dígitos>"
         Si aparecen varios CBU distintos dentro del bloque → ambigüedad.
      2) Fallback: único CBU global en todo el documento.
    """
    lines = _split_lines(text)

    # localizar bloques "Datos del destinatario"
    dest_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"datos\s+del\s+destinatario", ln, flags=re.IGNORECASE)]
    if dest_idxs:
        candidates = []
        for idx in dest_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + DEST_WINDOW + 1)])
            # "Cuenta <22d>"
            for m in _RE_LINEA_CUENTA.finditer(window):
                candidates.append(m.group(1))
            # "CBU/CVU <22d>"
            for m in _RE_LINEA_CBU_CVU.finditer(window):
                candidates.append(m.group(1))
            # por si estuviera el número suelto en ese bloque
            candidates.extend(_RE_CBU_22.findall(window))

        uniq = sorted(set(candidates))
        if len(uniq) == 1:
            return uniq[0]
        if len(uniq) > 1:
            raise ExtractionError("Ambigüedad: múltiples CBU en 'Datos del destinatario'.")

    # Fallback: único CBU global
    all_cbu = _RE_CBU_22.findall(text)
    uniq_all = sorted(set(all_cbu))
    if len(uniq_all) == 1:
        return uniq_all[0]
    if len(uniq_all) > 1:
        raise ExtractionError("Ambigüedad: múltiples CBU (22 dígitos) en el comprobante.")

    return None


# ───────────────────────────────────────────────────────────────────────────────
# API del extractor
# ───────────────────────────────────────────────────────────────────────────────

def extract(texto: str, *, cfg) -> dict:
    """
    Extrae {monto, fecha, cbu, alias} y valida contra lo esperado.

    Parámetros:
      - texto: OCR plano (string).
      - cfg: dict con lo esperado:
          cfg["monto"] (float)
          cfg["fecha"] ('YYYY-MM-DD')
          opcionales: cfg["cbu"], cfg["alias"]

    Retorna:
      dict(monto=float, fecha='YYYY-MM-DD', cbu=str|None, alias=None)

    Errores:
      - ExtractionError ante ambigüedades o faltantes.
    """
    if not texto:
        raise ExtractionError("Texto vacío.")

    txt = normalize_text_keep_lines(texto)

    fecha_iso = _extract_fecha_iso(txt)
    monto = _extract_monto(txt)
    cbu = _extract_cbu_destinatario(txt)

    result = ParseResult(monto=monto, fecha=fecha_iso, cbu=cbu, alias=None)

    # Validación de negocio: exact match con lo esperado
    validate_all_expected(
        result,
        expected_amount=cfg["monto"],
        expected_date_iso=cfg["fecha"],
        expected_cbu=cfg.get("cbu"),
        expected_alias=cfg.get("alias"),
    )

    return dict(monto=result.monto, fecha=result.fecha, cbu=result.cbu, alias=result.alias)
