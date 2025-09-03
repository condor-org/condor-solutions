"""
Extractor robusto para comprobantes de Allaria.

Patrones típicos observados:
- Encabezado con marca: "Allaria" o "Allaria +"
- Fecha corta: "31/08/25" (DD/MM/YY) o larga: "31/08/2025"
- Hora/ID pueden aparecer en la misma línea de fecha (no son necesarios)
- Secciones: "CUENTA ORIGEN", "CUENTA DESTINO", "MONTO ENVIADO", "DESCRIPCIÓN"
- CBU/alias figuran debajo del titular en cada sección de cuenta
- Monto suele estar en la línea siguiente a "MONTO ENVIADO"

Estrategia:
- Detección por keywords ("allaria", "comprobante de transferencia").
- Fecha: prioriza el primer match válido; soporta YY -> 20YY por heurística.
- CBU: busca dentro del bloque "CUENTA DESTINO" (ventana acotada).
- Monto: busca en la línea del título "MONTO ENVIADO" o en las siguientes líneas cercanas.
- Estricto: si se detectan múltiples candidatos relevantes, se lanza ExtractionError.

Salida:
- dict(monto: float, fecha: 'YYYY-MM-DD', cbu: str|None, alias: None)
"""

from __future__ import annotations
import re
import logging
from datetime import datetime, date
from typing import List, Optional, Tuple

from ..base import (
    ParseResult, ExtractionError,
    normalize_text_keep_lines, validate_all_expected
)

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────────────
# Detección del banco
# ───────────────────────────────────────────────────────────────────────────────

_ALLARIA_KEYS_PRIMARY = ("allaria", "allaria +")
_ALLARIA_KEYS_SECONDARY = ("comprobante de transferencia", "cuenta destino", "monto enviado")

def matches(texto: str) -> bool:
    """
    Devuelve True si el texto contiene señales claras de ser un comprobante de Allaria.
    Requiere marca principal ('allaria' / 'allaria +') y alguna señal secundaria.
    """
    t = (texto or "").lower()
    if not any(k in t for k in _ALLARIA_KEYS_PRIMARY):
        return False
    return any(k in t for k in _ALLARIA_KEYS_SECONDARY)


# ───────────────────────────────────────────────────────────────────────────────
# Regex y helpers reutilizados en este extractor
# ───────────────────────────────────────────────────────────────────────────────

# Dinero: AR (1.234,56) o US (1,234.56) con o sin '$'
_RE_MONEY_TOKEN = re.compile(r"\$?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})")
_RE_MONEY_LINE = re.compile(r"^\s*\$?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*$", re.MULTILINE)

# Fechas: DD/MM/YY(YY)
_RE_DATE = re.compile(r"\b([0-3]\d)[/\-]([0-1]\d)[/\-](\d{2}|\d{4})\b")

# CBU (22 dígitos)
_RE_CBU_22 = re.compile(r"\b(\d{22})\b")

# Señales de secciones
_RE_TIT_ORIGEN = re.compile(r"^\s*cuenta\s+origen\s*$", re.IGNORECASE | re.MULTILINE)
_RE_TIT_DESTINO = re.compile(r"^\s*cuenta\s+destino\s*$", re.IGNORECASE | re.MULTILINE)
_RE_TIT_MONTO = re.compile(r"^\s*monto\s+enviado\s*$", re.IGNORECASE | re.MULTILINE)

# Ventanas de búsqueda en líneas
DEST_WINDOW = 8     # líneas hacia abajo desde "CUENTA DESTINO"
MONTO_WINDOW = 4    # líneas hacia abajo desde "MONTO ENVIADO"


def _split_lines(text: str) -> List[str]:
    """Devuelve líneas normalizadas (sin vacías externas) para búsqueda local."""
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]


def _to_float_money(num_str: str) -> float:
    """
    Convierte token de dinero a float:
      - Si el último separador es coma => decimal AR (1.234,56).
      - Si el último separador es punto => decimal US (1,234.56).
    """
    s = num_str.strip()
    comma, dot = s.rfind(","), s.rfind(".")
    if comma > dot:
        return float(s.replace(".", "").replace(",", "."))
    return float(s.replace(",", ""))


def _iso_from_any_ddmmyy_or_yyyy(d: str, m: str, y: str) -> str:
    """
    Convierte fecha a 'YYYY-MM-DD'.
    Si viene YY, aplica heurística:
      - 00..79 => 2000..2079
      - 80..99 => 1980..1999 (muy raro en este dominio, pero soportado)
    """
    if len(y) == 2:
        yy = int(y)
        year = 2000 + yy if yy <= 79 else 1900 + yy
    else:
        year = int(y)
    dt = date(year=year, month=int(m), day=int(d))
    return dt.isoformat()


# ───────────────────────────────────────────────────────────────────────────────
# Extracción: FECHA
# ───────────────────────────────────────────────────────────────────────────────

def _extract_fecha_iso(text: str) -> str:
    """
    Toma la primera fecha válida del documento.
    Justificación: Allaria ubica la fecha de operación muy arriba (cerca del header).
    Si aparecen múltiples con valores distintos → ambigüedad.
    """
    dates = []
    for m in _RE_DATE.finditer(text):
        d, mo, y = m.group(1), m.group(2), m.group(3)
        try:
            iso = _iso_from_any_ddmmyy_or_yyyy(d, mo, y)
            dates.append(iso)
        except ValueError:
            continue

    if not dates:
        raise ExtractionError("No se encontró una fecha válida.")
    uniq = sorted(set(dates))
    if len(uniq) > 1:
        raise ExtractionError(f"Ambigüedad: múltiples fechas detectadas {uniq}.")
    return uniq[0]


# ───────────────────────────────────────────────────────────────────────────────
# Extracción: CBU de CUENTA DESTINO
# ───────────────────────────────────────────────────────────────────────────────

def _extract_cbu_destino(text: str) -> Optional[str]:
    """
    Busca el CBU dentro del bloque 'CUENTA DESTINO':
      - Encuentra el título 'CUENTA DESTINO'
      - Busca hacia abajo hasta DEST_WINDOW líneas el primer CBU de 22 dígitos
      - Si hay más de uno en la ventana → ambigüedad
    Fallback: si no hay bloque destino, intenta CBU único global (estricto).
    """
    lines = _split_lines(text)
    # localizar índice del bloque 'CUENTA DESTINO'
    dest_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"cuenta\s+destino", ln, flags=re.IGNORECASE)]
    if dest_idxs:
        candidates: List[str] = []
        for idx in dest_idxs:
            seg = "\n".join(lines[idx : min(len(lines), idx + DEST_WINDOW + 1)])
            candidates.extend(_RE_CBU_22.findall(seg))
        uniq = sorted(set(candidates))
        if len(uniq) == 1:
            return uniq[0]
        if len(uniq) > 1:
            raise ExtractionError("Ambigüedad: múltiples CBU detectados en 'CUENTA DESTINO'.")

    # Fallback muy estricto: único CBU global
    all_cbu = _RE_CBU_22.findall(text)
    uniq_all = sorted(set(all_cbu))
    if len(uniq_all) == 1:
        return uniq_all[0]
    if len(uniq_all) > 1:
        raise ExtractionError("Ambigüedad: múltiples CBU (22 dígitos) en el comprobante.")

    return None


# ───────────────────────────────────────────────────────────────────────────────
# Extracción: MONTO (desde "MONTO ENVIADO" o línea limpia)
# ───────────────────────────────────────────────────────────────────────────────

def _extract_monto(text: str) -> float:
    """
    Preferencia:
      1) Buscar el título 'MONTO ENVIADO' y tomar el primer monto en las siguientes
         MONTO_WINDOW líneas (suele estar en la inmediata siguiente).
         - Si hay >1 montos distintos en esa ventana → ambigüedad.
      2) Línea limpia con solo un monto.
      3) Único token de dinero en todo el texto (o el mismo repetido).
    """
    lines = _split_lines(text)

    # 1) Ventana desde 'MONTO ENVIADO'
    tit_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"monto\s+enviado", ln, flags=re.IGNORECASE)]
    if tit_idxs:
        candidates: List[str] = []
        for idx in tit_idxs:
            seg = "\n".join(lines[idx : min(len(lines), idx + MONTO_WINDOW + 1)])
            candidates.extend(_RE_MONEY_TOKEN.findall(seg))
        if candidates:
            uniq = sorted(set(candidates))
            if len(uniq) == 1:
                return _to_float_money(uniq[0])
            raise ExtractionError("Ambigüedad: múltiples montos distintos cerca de 'MONTO ENVIADO'.")

    # 2) Línea limpia
    line_matches = _RE_MONEY_LINE.findall(text)
    if len(line_matches) == 1:
        return _to_float_money(line_matches[0])
    if len(line_matches) > 1:
        raise ExtractionError("Ambigüedad: múltiples líneas de monto detectadas.")

    # 3) Tokens globales
    tokens = _RE_MONEY_TOKEN.findall(text)
    if not tokens:
        raise ExtractionError("No se encontró monto en el comprobante.")
    uniq = sorted(set(tokens))
    if len(uniq) == 1:
        return _to_float_money(uniq[0])
    raise ExtractionError(f"Ambigüedad: múltiples montos distintos detectados ({', '.join(uniq[:3])}).")


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

    Reglas de error:
      - Se lanza ExtractionError ante ambigüedades o faltantes.
    """
    if not texto:
        raise ExtractionError("Texto vacío.")

    txt = normalize_text_keep_lines(texto)

    fecha_iso = _extract_fecha_iso(txt)
    cbu = _extract_cbu_destino(txt)
    monto = _extract_monto(txt)

    result = ParseResult(monto=monto, fecha=fecha_iso, cbu=cbu, alias=None)

    # Validación de negocio (exact match con lo esperado)
    validate_all_expected(
        result,
        expected_amount=cfg["monto"],
        expected_date_iso=cfg["fecha"],
        expected_cbu=cfg.get("cbu"),
        expected_alias=cfg.get("alias"),
    )

    return dict(monto=result.monto, fecha=result.fecha, cbu=result.cbu, alias=result.alias)
