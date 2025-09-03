"""
Extractor robusto para comprobantes de Cuenta DNI (BAPRO).

Patrones frecuentes:
- Marca: "Cuenta DNI"
- Títulos: "Comprobante de transferencia", "Importe", "Origen", "Para"
- Destino: "Alias: <alias>" y/o CUIL; a veces aparece CVU/CBU
- Fecha/hora: "DD/MM/YYYY HH:MM(:SS)?hs" (se devuelve solo la fecha)

Estrategia:
- Detección por keywords.
- Monto: ventana acotada desde "Importe" → línea limpia → único token global.
- Fecha: preferencia por fecha con hora "hs"; fallback a fecha única global.
- Destino: preferencia por "Alias:" en bloque "Para"; si falta, buscar CBU/CVU de 22 dígitos
  cerca de "Para"; último recurso: único 22 dígitos global.

Salida:
- dict(monto: float, fecha: 'YYYY-MM-DD', cbu: str|None, alias: str|None)
"""

from __future__ import annotations
import re
import logging
from datetime import datetime
from typing import List, Optional

from ..base import (
    ParseResult, ExtractionError,
    normalize_text_keep_lines, validate_all_expected
)

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────────────
# Detección del banco
# ───────────────────────────────────────────────────────────────────────────────

import re

_CDNI_SECONDARY = ("comprobante de transferencia", "importe", "origen", "para", "alias:")

def matches(texto: str) -> bool:
    """
    True si el comprobante parece de Cuenta DNI.
    Acepta 'cuenta dni' con espacios, saltos de línea o múltiple whitespace.
    """
    t = (texto or "").lower()
    # cuenta + dni con cualquier whitespace entre medio
    if not re.search(r"cuenta\s+dni", t, flags=re.IGNORECASE | re.DOTALL):
        return False
    return any(k in t for k in _CDNI_SECONDARY)


# ───────────────────────────────────────────────────────────────────────────────
# Regex/utilidades específicas
# ───────────────────────────────────────────────────────────────────────────────

# Dinero: AR (1.234,56) o sin miles (51400,00), con/sin símbolo $
_RE_MONEY_TOKEN = re.compile(r"\$?\s*([0-9]{1,3}(?:[.,]\d{3})*,\d{2}|[0-9]+,\d{2})")
_RE_MONEY_LINE  = re.compile(r"^\s*\$?\s*([0-9]{1,3}(?:[.,]\d{3})*,\d{2}|[0-9]+,\d{2})\s*$", re.MULTILINE)

# Títulos/bloques
_RE_TIT_IMPORTE = re.compile(r"^\s*importe\s*$", re.IGNORECASE | re.MULTILINE)
_RE_TIT_PARA    = re.compile(r"^\s*para\s*$", re.IGNORECASE | re.MULTILINE)

# Fecha: "DD/MM/YYYY" con hora opcional y sufijo "hs"
_RE_DATE_CORE   = re.compile(r"\b([0-3]\d)/([0-1]\d)/(\d{4})\b")
_RE_DATE_WITH_H = re.compile(r"\b([0-3]\d)/([0-1]\d)/(\d{4})\s+[0-2]\d:[0-5]\d(?::[0-5]\d)?\s*hs\b", re.IGNORECASE)

# Alias estricto (6–20, alfanumérico y puntos, sin empezar/terminar con '.')
_RE_ALIAS_LABEL = re.compile(r"alias:\s*([A-Za-z0-9](?:[A-Za-z0-9\.]{4,18})[A-Za-z0-9])", re.IGNORECASE)

# CBU/CVU de 22 dígitos
_RE_22DIG = re.compile(r"\b(\d{22})\b")

# Ventanas de búsqueda relativas (en líneas)
AMOUNT_WINDOW = 4
DEST_WINDOW   = 10


def _split_lines(text: str) -> List[str]:
    """Devuelve líneas no vacías y recortadas."""
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]


def _to_float_ar(token: str) -> float:
    """Convierte '51.400,00' o '51400,00' a 51400.00."""
    s = token.replace(".", "").replace(",", ".")
    return float(s)


def _iso_from_ddmmyyyy(d: str, m: str, y: str) -> str:
    """Devuelve 'YYYY-MM-DD' validando."""
    dt = datetime(year=int(y), month=int(m), day=int(d)).date()
    return dt.isoformat()


# ───────────────────────────────────────────────────────────────────────────────
# Extracción de campos
# ───────────────────────────────────────────────────────────────────────────────

def _extract_monto(txt: str) -> float:
    """
    Preferencia:
      1) Ventana desde 'Importe' (AMOUNT_WINDOW líneas siguientes).
      2) Línea limpia con solo monto.
      3) Único token global (o el mismo repetido).
    """
    lines = _split_lines(txt)

    # 1) Ventana 'Importe'
    tit_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"importe", ln, flags=re.IGNORECASE)]
    if tit_idxs:
        candidates = []
        for idx in tit_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + AMOUNT_WINDOW + 1)])
            candidates.extend(_RE_MONEY_TOKEN.findall(window))
        if candidates:
            uniq = sorted(set(candidates))
            if len(uniq) == 1:
                return _to_float_ar(uniq[0])
            raise ExtractionError("Ambigüedad: múltiples montos distintos cerca de 'Importe'.")

    # 2) Línea limpia
    line_matches = _RE_MONEY_LINE.findall(txt)
    if len(line_matches) == 1:
        return _to_float_ar(line_matches[0])
    if len(line_matches) > 1:
        raise ExtractionError("Ambigüedad: múltiples líneas con solo un monto.")

    # 3) Tokens globales
    tokens = _RE_MONEY_TOKEN.findall(txt)
    if not tokens:
        raise ExtractionError("No se encontró monto en el comprobante.")
    uniq = sorted(set(tokens))
    if len(uniq) == 1:
        return _to_float_ar(uniq[0])
    raise ExtractionError(f"Ambigüedad: múltiples montos distintos detectados ({', '.join(uniq[:3])}).")


def _extract_fecha_iso(txt: str) -> str:
    """
    Preferencia:
      1) Fecha con hora 'hs' (línea que tenga fecha + hora), devuelve solo fecha.
      2) Fallback: fecha única global DD/MM/YYYY.
    """
    with_h = _RE_DATE_WITH_H.findall(txt)
    if with_h:
        # puede haber más de una línea con hora; validar unicidad de fechas
        dates = {_iso_from_ddmmyyyy(d, m, y) for (d, m, y) in with_h}
        if len(dates) == 1:
            return next(iter(dates))
        raise ExtractionError(f"Ambigüedad: múltiples fechas con hora detectadas {sorted(dates)}.")

    # Fallback: fecha única global
    all_dates = [_iso_from_ddmmyyyy(m.group(1), m.group(2), m.group(3)) for m in _RE_DATE_CORE.finditer(txt)]
    if not all_dates:
        raise ExtractionError("No se encontró una fecha válida.")
    uniq = sorted(set(all_dates))
    if len(uniq) == 1:
        return uniq[0]
    raise ExtractionError(f"Ambigüedad: múltiples fechas detectadas {uniq}.")


def _extract_destino(txt: str) -> tuple[Optional[str], Optional[str]]:
    """
    Preferencia:
      1) Dentro del bloque 'Para' → 'Alias: <alias>'.
      2) Dentro del bloque 'Para' → 22 dígitos (CBU/CVU).
      3) Fallback global: 'Alias:' en todo el texto.
      4) Fallback global: único 22 dígitos.
    """
    lines = _split_lines(txt)

    # 1/2) Ventana desde 'Para'
    para_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"para", ln, flags=re.IGNORECASE)]
    if para_idxs:
        for idx in para_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + DEST_WINDOW + 1)])
            m_alias = _RE_ALIAS_LABEL.search(window)
            if m_alias:
                return (None, m_alias.group(1))
            cands = _RE_22DIG.findall(window)
            uniq_cbu = sorted(set(cands))
            if len(uniq_cbu) == 1:
                return (uniq_cbu[0], None)
            if len(uniq_cbu) > 1:
                raise ExtractionError("Ambigüedad: múltiples CBU/CVU cerca de 'Para'.")

    # 3) Alias global
    m_alias_global = _RE_ALIAS_LABEL.search(txt)
    if m_alias_global:
        return (None, m_alias_global.group(1))

    # 4) Único CBU/CVU global
    all_22 = _RE_22DIG.findall(txt)
    uniq_all = sorted(set(all_22))
    if len(uniq_all) == 1:
        return (uniq_all[0], None)
    if len(uniq_all) > 1:
        raise ExtractionError("Ambigüedad: múltiples CBU/CVU (22 dígitos) en el comprobante.")

    return (None, None)


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
      dict(monto=float, fecha='YYYY-MM-DD', cbu=str|None, alias=str|None)
    """
    if not texto:
        raise ExtractionError("Texto vacío.")

    txt = normalize_text_keep_lines(texto)

    monto = _extract_monto(txt)
    fecha_iso = _extract_fecha_iso(txt)
    cbu, alias = _extract_destino(txt)

    result = ParseResult(monto=monto, fecha=fecha_iso, cbu=cbu, alias=alias)

    # Validación de negocio (exact match con lo esperado)
    validate_all_expected(
        result,
        expected_amount=cfg["monto"],
        expected_date_iso=cfg["fecha"],
        expected_cbu=cfg.get("cbu"),
        expected_alias=cfg.get("alias"),
    )

    return dict(monto=result.monto, fecha=result.fecha, cbu=result.cbu, alias=result.alias)
