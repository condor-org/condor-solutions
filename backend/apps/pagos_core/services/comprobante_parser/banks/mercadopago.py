"""
Extractor robusto para comprobantes de Mercado Pago.

Patrones habituales:
- Marca: "mercado pago"
- Bloques: "De" (origen) / "Para" (destino)
- Identificadores: "CVU:" o "CBU:" (22 dígitos)
- Monto: puede venir como entero con separadores (p. ej., "$ 14.000") o con decimales ("$ 14.000,50")
- Fecha larga en español: "Miércoles, 18 de junio de 2025 a las 20:29 hs"
  (aceptamos sin día de la semana y sin la hora también)

Estrategia (estricta con fallbacks):
- `matches`: requiere la marca "mercado pago".
- `fecha`: prioriza "DD de <mes> de YYYY" (con o sin día de semana, con o sin "a las HH:MM hs").
- `monto`: preferencia global por tokens con '$'; si no hay, línea limpia "monto-only";
           último recurso: tokens globales; en todos los casos se ignoran enteros grandes "planos".
- `destino (CVU/CBU)`: busca en el bloque "Para" (ventana acotada). Si no se encuentra,
   último recurso: único 22 dígitos global. Si hay múltiples candidatos → error.
- `alias`: no suele mostrarse en MP → devolvemos None.

Salida:
- dict(monto: float, fecha: 'YYYY-MM-DD', cbu: str|None, alias: None)
"""

from __future__ import annotations
import re
import logging
from datetime import date
from typing import List, Optional

from ..base import (
    ParseResult, ExtractionError,
    normalize_text_keep_lines, validate_all_expected
)

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────────────
# Detección del banco
# ───────────────────────────────────────────────────────────────────────────────

_MP_PRIMARY = ("mercado pago",)

def matches(texto: str) -> bool:
    """
    True si el OCR contiene la marca principal 'mercado pago'.
    """
    t = (texto or "").lower()
    return any(k in t for k in _MP_PRIMARY)


# ───────────────────────────────────────────────────────────────────────────────
# Regex y utilidades específicas
# ───────────────────────────────────────────────────────────────────────────────

# Mapeo de meses en español (toleramos tildes/minúsculas)
_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Día de la semana opcional + "DD de <mes> de YYYY" + (opcional) "a las HH:MM (hs)"
_RE_FECHA_ES_LARGA = re.compile(
    r"(?:(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s*,?\s+)?"
    r"([0-3]?\d)\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})"
    r"(?:\s+a\s+las\s+[0-2]\d:[0-5]\d(?:\s*hs)?)?",
    re.IGNORECASE
)

# Tokens de dinero (símbolo $ opcional)
_RE_MONEY_TOKEN = re.compile(
    r"\$?\s*("                              # grupo 1 = número
    r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)"  # miles + opcional decimales
    r"|"
    r"(?:\d+(?:[.,]\d{2})?)"                    # entero simple o con decimales
    r")"
)

# Línea “limpia” con solo el monto
_RE_MONEY_LINE = re.compile(
    r"^\s*\$?\s*("
    r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)"
    r"|"
    r"(?:\d+(?:[.,]\d{2})?)"
    r")\s*$",
    re.MULTILINE
)

# Tokens que tienen '$' explícito
_RE_DOLLAR = re.compile(
    r"\$\s*("
    r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)"
    r"|"
    r"(?:\d+(?:[.,]\d{2})?)"
    r")"
)

# CBU/CVU (22 dígitos)
_RE_22DIG = re.compile(r"\b(\d{22})\b")

# Encabezados de bloques
_RE_TIT_PARA = re.compile(r"^\s*para\s*$", re.IGNORECASE | re.MULTILINE)

# Ventanas de búsqueda relativas (en líneas)
DEST_WINDOW = 12   # desde "Para" hacia abajo


def _split_lines(text: str) -> List[str]:
    """Devuelve líneas no vacías y recortadas (para búsquedas de bloque)."""
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]


def _to_float_money(token: str) -> float:
    """
    Convierte un token monetario a float.
    - Último separador visible coma → coma decimal (AR).
    - Último separador punto con 2 decimales → punto decimal.
    - Entero o miles → remueve separadores.
    """
    s = token.strip()
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")
    if last_comma > last_dot:
        return float(s.replace(".", "").replace(",", "."))
    if last_dot > -1 and (len(s) - last_dot - 1) == 2:
        return float(s.replace(",", ""))
    return float(s.replace(".", "").replace(",", ""))


def _iso_from_fecha_larga(d: str, mes: str, y: str) -> str:
    """Convierte 'DD de <mes> de YYYY' a 'YYYY-MM-DD' (valida mes y la fecha)."""
    m = _MONTHS.get(mes.lower())
    if not m:
        norm = (mes.lower()
                  .replace("á", "a")
                  .replace("é", "e")
                  .replace("í", "i")
                  .replace("ó", "o")
                  .replace("ú", "u"))
        m = _MONTHS.get(norm)
    if not m:
        raise ExtractionError(f"Mes no reconocido en fecha: {mes}")
    return date(int(y), int(m), int(d)).isoformat()


def _is_plain_big_integer(token: str, *, min_len: int = 7) -> bool:
    """
    True si el token es un entero sin separadores ni decimales, y con longitud >= min_len.
    Sirve para descartar IDs/números de operación (p. ej., '115608721914').
    """
    s = token.strip()
    if "." in s or "," in s:
        return False
    return s.isdigit() and len(s) >= min_len


# ───────────────────────────────────────────────────────────────────────────────
# Extracción de campos (estricta con fallbacks ordenados)
# ───────────────────────────────────────────────────────────────────────────────

def _extract_fecha_iso(txt: str) -> str:
    """
    Busca fechas del tipo 'DD de <mes> de YYYY' (con/sin día de semana, con/sin hora).
    Si encuentra múltiples fechas distintas → ambigüedad.
    """
    candidates = []
    for m in _RE_FECHA_ES_LARGA.finditer(txt):
        try:
            iso = _iso_from_fecha_larga(m.group(1), m.group(2), m.group(3))
            candidates.append(iso)
        except Exception:
            continue

    if not candidates:
        raise ExtractionError("No se encontró una fecha válida (ej.: '18 de junio de 2025').")

    uniq = sorted(set(candidates))
    if len(uniq) == 1:
        return uniq[0]
    raise ExtractionError(f"Ambigüedad: múltiples fechas detectadas {uniq}.")


def _extract_monto(txt: str) -> float:
    """
    Preferencia estricta:
      1) Tokens con '$' en todo el documento → desambiguación por valor.
      2) Líneas 'monto-only' (global), ignorando enteros grandes planos → desambiguación por valor.
      3) Tokens monetarios globales, ignorando enteros grandes planos → desambiguación por valor.
    En cualquier etapa, si quedan >1 valores distintos → ambigüedad.
    """
    # 1) Con '$' (global)
    dollar_tokens = _RE_DOLLAR.findall(txt)
    if dollar_tokens:
        uniq_vals = sorted({ _to_float_money(t) for t in dollar_tokens })
        if len(uniq_vals) == 1:
            return uniq_vals[0]
        raise ExtractionError("Ambigüedad: múltiples montos distintos con '$' en el comprobante.")

    # 2) Líneas 'monto-only' (ignorar IDs/enteros planos)
    line_matches = [t for t in _RE_MONEY_LINE.findall(txt) if not _is_plain_big_integer(t)]
    if line_matches:
        uniq_vals = sorted({ _to_float_money(t) for t in line_matches })
        if len(uniq_vals) == 1:
            return uniq_vals[0]
        raise ExtractionError("Ambigüedad: múltiples líneas con solo un monto.")

    # 3) Tokens globales (ignorar IDs/enteros planos)
    tokens = [t for t in _RE_MONEY_TOKEN.findall(txt) if not _is_plain_big_integer(t)]
    if not tokens:
        raise ExtractionError("No se encontró monto en el comprobante.")
    uniq_vals = sorted({ _to_float_money(t) for t in tokens })
    if len(uniq_vals) == 1:
        return uniq_vals[0]
    raise ExtractionError("Ambigüedad: múltiples montos distintos detectados.")


def _extract_cvu_destino(txt: str) -> Optional[str]:
    """
    Busca el CVU/CBU del bloque 'Para':
      - Encuentra la línea 'Para' y toma el primer 22 dígitos dentro de las
        DEST_WINDOW líneas siguientes (bloque destino).
      - Si hay más de un 22 dígitos distinto en ese bloque → ambigüedad.
      - Fallback: único 22 dígitos global en todo el texto.
    """
    lines = _split_lines(txt)
    para_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"para", ln, flags=re.IGNORECASE)]

    if para_idxs:
        candidates = []
        for idx in para_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + DEST_WINDOW + 1)])
            candidates.extend(_RE_22DIG.findall(window))
        uniq = sorted(set(candidates))
        if len(uniq) == 1:
            return uniq[0]
        if len(uniq) > 1:
            raise ExtractionError("Ambigüedad: múltiples CVU/CBU detectados en el bloque 'Para'.")

    # Fallback: único 22 dígitos global
    all_22 = _RE_22DIG.findall(txt)
    uniq_all = sorted(set(all_22))
    if len(uniq_all) == 1:
        return uniq_all[0]
    if len(uniq_all) > 1:
        raise ExtractionError("Ambigüedad: múltiples CVU/CBU (22 dígitos) en el comprobante.")

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
    """
    if not texto:
        raise ExtractionError("Texto vacío.")

    txt = normalize_text_keep_lines(texto)

    fecha_iso = _extract_fecha_iso(txt)
    monto = _extract_monto(txt)
    cbu = _extract_cvu_destino(txt)   # puede ser CVU; lo devolvemos en 'cbu' para validar contra cfg["cbu"]

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
