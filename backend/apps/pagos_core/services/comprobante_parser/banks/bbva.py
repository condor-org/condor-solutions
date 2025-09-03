"""
Extractor genérico/robusto para comprobantes BBVA.

Diseño:
- Detección por palabras clave: 'BBVA', 'Banca Online', 'Banco BBVA'.
- Monto: prioriza líneas “limpias” con formato dinero (ej. "$ 1.234,56"), con o sin símbolo.
- Fecha: prioriza fecha de operación en formato 'DD/MM/YYYY' (o 'DD-MM-YYYY'),
         preferentemente si aparece junto a una hora en la línea siguiente o la misma línea.
- CBU/CVU del DESTINATARIO: prioriza etiqueta 'CBU/CVU del destinatario'.
  Fallback: CBU (22 dígitos) cercano a la palabra 'destinatario' en una ventana de ±5 líneas.
  Último recurso: único CBU de 22 dígitos en todo el texto.

Reglas de estrictez:
- Si se detectan múltiples candidatos plausibles para monto/fecha/CBU, se lanza ExtractionError.
- Los fallbacks están ordenados para minimizar falsos positivos.

Salida:
- dict(monto: float, fecha: 'YYYY-MM-DD', cbu: str|None, alias: None)

Validación:
- Se compara con lo esperado vía validate_all_expected (monto / fecha / cbu/alias).
"""

from __future__ import annotations
import re
import logging
from datetime import datetime
from typing import List, Tuple, Optional

from ..base import (
    ParseResult, ExtractionError,
    normalize_text_keep_lines, validate_all_expected
)

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────────────
# Detección del banco
# ───────────────────────────────────────────────────────────────────────────────

_BBVA_KEYWORDS = (
    "bbva",                             # marca
    "banco bbva",                       # variante
    "banca online",                     # footer típico
    "esta operación se realizó en banca online",  # frase habitual
    "transferiste a",                   # verbo que usan en envíos
    "número de referencia",             # etiqueta común
)

def matches(texto: str) -> bool:
    """
    True si el OCR contiene señales claras de ser BBVA.
    Usamos un set de keywords robustas y en minúsculas.
    """
    t = (texto or "").lower()
    # Evita falsos positivos exigiendo al menos 'bbva' o 'banco bbva'
    if "bbva" not in t and "banco bbva" not in t:
        return False
    # Y además alguna de las otras señales típicas
    return any(k in t for k in _BBVA_KEYWORDS)


# ───────────────────────────────────────────────────────────────────────────────
# Regex y helpers: monto / fecha / cbu
# ───────────────────────────────────────────────────────────────────────────────

# Dinero: admite AR (1.234,56) y US (1,234.56) con o sin $
_RE_MONEY_TOKEN = re.compile(
    r"\$?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})"
)

# Línea “limpia” de dinero (solo el monto, con o sin $). Reduce falsos positivos.
_RE_MONEY_LINE = re.compile(
    r"^\s*\$?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*$",
    re.MULTILINE
)

# Fechas habituales en comprobantes BBVA
_RE_DATE_DDMMYYYY = re.compile(r"\b([0-3]\d)[/\-]([0-1]\d)[/\-](\d{4})\b")

# Hora (para preferir fechas con hora cercana)
_RE_TIME = re.compile(r"\b([0-2]\d):([0-5]\d)(?::([0-5]\d))?\b")

# CBU con etiqueta clara de destinatario
_RE_CBU_DEST_LABEL = re.compile(
    r"CBU/CVU\s+del\s+destinatario\s+(\d{22})",
    re.IGNORECASE
)
# Otros labels posibles (por si cambia levemente la frase)
_RE_CBU_DEST_ALT = re.compile(
    r"(?:cbu|cvu)[/\s]*(?:cvu|cbu)?\s*(?:del|de)\s*destinatario[:\s]*?(\d{22})",
    re.IGNORECASE
)

# CBU crudo (22 dígitos)
_RE_CBU_22 = re.compile(r"\b(\d{22})\b")

# Ventana de proximidad (en líneas) para asociar un CBU a 'destinatario'
_WINDOW = 5


def _to_float_money(num_str: str) -> float:
    """
    Convierte un token monetario a float.
    Heurística:
      - Si el último separador es coma, interpretamos 'AR' (1.234,56).
      - Si el último separador es punto, interpretamos 'US' (1,234.56).
    """
    s = num_str.strip()
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")
    # Default AR si ambos existen y la coma está a la derecha (decimal)
    if last_comma > last_dot:
        # AR: quitar puntos de miles, cambiar coma por punto
        return float(s.replace(".", "").replace(",", "."))
    # US: quitar comas de miles
    return float(s.replace(",", ""))


def _iso_from_ddmmyyyy_or_dash(d: str, m: str, y: str) -> str:
    """Normaliza a 'YYYY-MM-DD' y valida fecha real."""
    dt = datetime(year=int(y), month=int(m), day=int(d)).date()
    return dt.isoformat()


def _split_lines(text: str) -> List[str]:
    """Devuelve el texto en líneas, sin vacías extremas, para búsquedas locales."""
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]


# ───────────────────────────────────────────────────────────────────────────────
# Extracción de MONTO (orden de preferencia con estrictez)
# ───────────────────────────────────────────────────────────────────────────────

def _extract_amount(text: str) -> float:
    """
    Orden de preferencia:
      1) Línea “limpia” con un solo monto → único candidato válido.
      2) Si no hay línea limpia, buscar tokens de dinero en todo el texto.
         - Si hay exactamente 1 token → lo tomamos.
         - Si hay >1 → ambigüedad (falla).
    """
    # 1) Línea limpia
    line_matches = _RE_MONEY_LINE.findall(text)
    if len(line_matches) == 1:
        return _to_float_money(line_matches[0])
    if len(line_matches) > 1:
        raise ExtractionError("Ambigüedad: múltiples líneas de monto detectadas.")

    # 2) Tokens en todo el texto
    tokens = _RE_MONEY_TOKEN.findall(text)
    if not tokens:
        raise ExtractionError("No se encontró monto en el comprobante.")
    if len(tokens) > 1:
        # Permitimos un caso común: mismo monto repetido 2 veces (encabezado + cuerpo).
        uniq = {t for t in tokens}
        if len(uniq) == 1:
            return _to_float_money(tokens[0])
        raise ExtractionError(f"Ambigüedad: múltiples montos distintos detectados ({', '.join(list(uniq)[:3])}).")

    return _to_float_money(tokens[0])


# ───────────────────────────────────────────────────────────────────────────────
# Extracción de FECHA (prioriza fecha con hora cercana)
# ───────────────────────────────────────────────────────────────────────────────

def _extract_date_iso(text: str) -> str:
    """
    Estrategia:
      - Parsear todas las fechas DD/MM/YYYY o DD-MM-YYYY.
      - Si alguna fecha tiene una hora en la MISMA línea o en la siguiente,
        priorizarla (suele ser la fecha de operación).
      - Si queda única fecha → devolver.
      - Si hay múltiples fechas diferentes → ambigüedad.
    """
    lines = _split_lines(text)

    # 1) fechas por línea + marcas de hora cercanas
    dated_lines: List[Tuple[int, str]] = []
    for i, ln in enumerate(lines):
        for m in _RE_DATE_DDMMYYYY.finditer(ln):
            d, mo, y = m.group(1), m.group(2), m.group(3)
            iso = _iso_from_ddmmyyyy_or_dash(d, mo, y)
            dated_lines.append((i, iso))

    if not dated_lines:
        raise ExtractionError("No se encontró una fecha válida.")

    def has_near_time(idx: int) -> bool:
        # hora en la misma línea o la siguiente
        if _RE_TIME.search(lines[idx]):
            return True
        if idx + 1 < len(lines) and _RE_TIME.search(lines[idx + 1]):
            return True
        return False

    # 2) priorizar las que tienen hora cercana
    with_time = [iso for (i, iso) in dated_lines if has_near_time(i)]
    uniq_with_time = sorted(set(with_time))
    if len(uniq_with_time) == 1:
        return uniq_with_time[0]
    if len(uniq_with_time) > 1:
        raise ExtractionError(f"Ambigüedad: múltiples fechas con hora cercana {uniq_with_time}.")

    # 3) si no hay fechas con hora cercana, revisar unicidad global
    uniq_all = sorted(set(iso for _, iso in dated_lines))
    if len(uniq_all) == 1:
        return uniq_all[0]

    raise ExtractionError(f"Ambigüedad: múltiples fechas detectadas {uniq_all}.")


# ───────────────────────────────────────────────────────────────────────────────
# Extracción de CBU del DESTINATARIO (label → proximidad → único global)
# ───────────────────────────────────────────────────────────────────────────────

def _extract_cbu_destinatario(text: str) -> Optional[str]:
    """
    Orden de preferencia para CBU del destinatario:
      1) Etiqueta explícita 'CBU/CVU del destinatario <22dígitos>'.
      2) Etiqueta alterna equivalente (fallas menores de OCR).
      3) CBU único (22 dígitos) dentro de una ventana de ±5 líneas alrededor
         de una línea que mencione 'destinatario'.
      4) Único CBU de 22 dígitos en todo el texto.
      Si hay múltiples candidatos en cualquier paso → ambigüedad.
    """
    # 1) Etiqueta exacta
    m = _RE_CBU_DEST_LABEL.search(text)
    if m:
        return m.group(1)

    # 2) Variante de etiqueta
    m2 = _RE_CBU_DEST_ALT.search(text)
    if m2:
        return m2.group(1)

    # 3) Proximidad a 'destinatario'
    lines = _split_lines(text)
    dest_idxs = [i for i, ln in enumerate(lines) if "destinatario" in ln.lower()]
    if dest_idxs:
        candidates: List[str] = []
        for idx in dest_idxs:
            start = max(0, idx - _WINDOW)
            end = min(len(lines), idx + _WINDOW + 1)
            segment = "\n".join(lines[start:end])
            cand = _RE_CBU_22.findall(segment)
            candidates.extend(cand)
        uniq = sorted(set(candidates))
        if len(uniq) == 1:
            return uniq[0]
        if len(uniq) > 1:
            raise ExtractionError("Ambigüedad: múltiples CBU cerca de 'destinatario'.")

    # 4) Único global
    all_cbu = _RE_CBU_22.findall(text)
    uniq_all = sorted(set(all_cbu))
    if len(uniq_all) == 1:
        return uniq_all[0]
    if len(uniq_all) > 1:
        raise ExtractionError("Ambigüedad: múltiples CBU (22 dígitos) en el comprobante.")

    # Puede no existir (algunas transferencias muestran alias en lugar de CBU)
    return None


# ───────────────────────────────────────────────────────────────────────────────
# API del extractor
# ───────────────────────────────────────────────────────────────────────────────

def extract(texto: str, *, cfg) -> dict:
    """
    Extrae campos de un comprobante BBVA y valida contra lo esperado.

    Parámetros:
      - texto: OCR ya plano (string).
      - cfg: dict con lo esperado del negocio:
          cfg["monto"] (float),
          cfg["fecha"] ('YYYY-MM-DD'),
          opcionales: cfg["cbu"], cfg["alias"]

    Retorna:
      dict(monto=float, fecha='YYYY-MM-DD', cbu=str|None, alias=None)

    Errores:
      - ExtractionError si hay ambigüedad o falta un dato clave.
    """
    if not texto:
        raise ExtractionError("Texto vacío.")

    # Mantener saltos de línea para aprovechar el layout (líneas “limpias”, proximidad, etc.)
    txt = normalize_text_keep_lines(texto)

    # Monto
    monto = _extract_amount(txt)

    # Fecha (preferencia: con hora cercana)
    fecha_iso = _extract_date_iso(txt)

    # CBU del destinatario (etiqueta → proximidad → único global)
    cbu = _extract_cbu_destinatario(txt)

    # Alias: BBVA suele imprimir CBU o alias, no ambos; si se necesita, se puede agregar patrón específico.
    alias = None

    result = ParseResult(monto=monto, fecha=fecha_iso, cbu=cbu, alias=alias)

    # Validación de negocio (estricta): compara con lo esperado
    validate_all_expected(
        result,
        expected_amount=cfg["monto"],
        expected_date_iso=cfg["fecha"],
        expected_cbu=cfg.get("cbu"),
        expected_alias=cfg.get("alias"),
    )

    return dict(monto=result.monto, fecha=result.fecha, cbu=result.cbu, alias=result.alias)
