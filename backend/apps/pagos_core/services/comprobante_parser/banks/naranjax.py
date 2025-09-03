"""
Extractor robusto para comprobantes de Naranja X / NaranjaX.

Patrones habituales:
- Encabezado: "NaranjaX" o "Naranja X"
- Títulos: "Comprobante de transferencia", "Cuenta origen", "Cuenta destino"
- Etiquetas: "CBU", "CVU", "CUIL", "COELSA ID"
- Fecha: "02/JUL/2025-15:30 h" (mes abreviado en español, hora opcional)
- Monto cerca de "Enviaste" (a veces con ruido: "$ 10.000.000 ºº")

Estrategia de extracción (estricta con fallbacks controlados):
- Fecha: parsear DD/<mes_abrev>/YYYY con hora opcional; convierte a YYYY-MM-DD.
- Monto: preferencia por la ventana bajo "Enviaste"; admite entero o decimal,
         y tolera basura al final (p. ej. "ºº"). Si hay múltiples montos distintos → error.
- CBU/CVU DESTINO: buscar en el bloque "Cuenta destino", privilegiando líneas
         con etiqueta "CVU" o "CBU". Si hay >1 candidatos distintos en la ventana → error.
         Último recurso: único CBU/CVU (22 dígitos) global.

Salida:
- dict(monto: float, fecha: 'YYYY-MM-DD', cbu: str|None, alias: None)

Validación:
- Se compara con lo esperado (monto/fecha/cbu/alias) usando validate_all_expected.
"""

from __future__ import annotations
import re
import logging
from datetime import date
from typing import List, Optional, Tuple

from ..base import (
    ParseResult, ExtractionError,
    normalize_text_keep_lines, validate_all_expected
)

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────────────
# Detección del banco
# ───────────────────────────────────────────────────────────────────────────────

_NX_PRIMARY = ("naranjax", "naranja x")
_NX_SECONDARY = ("comprobante de transferencia", "cuenta origen", "cuenta destino", "banco virtual", "coelsa id")

def matches(texto: str) -> bool:
    """
    True si el OCR contiene señales claras de Naranja X.
    Requiere al menos una clave primaria y, preferentemente, alguna secundaria.
    """
    t = (texto or "").lower()
    if not any(k in t for k in _NX_PRIMARY):
        return False
    return any(k in t for k in _NX_SECONDARY)


# ───────────────────────────────────────────────────────────────────────────────
# Regex y utilidades específicas de Naranja X
# ───────────────────────────────────────────────────────────────────────────────

# Meses abreviados en español que suelen aparecer (MAY, JUN, JUL, AGO, SEP, OCT, NOV, DIC, etc.)
# También toleramos variantes en minúsculas.
_MONTHS = {
    "ene": 1, "jan": 1,  # por si apareciera en inglés/mixto
    "feb": 2,
    "mar": 3,
    "abr": 4, "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8, "aug": 8,
    "sep": 9, "set": 9, "sept": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12, "dec": 12,
}

# Fecha "02/JUL/2025-15:30 h" o "02/JUL/2025 - 15:30" o "02/JUL/2025"
_RE_DATE_MONTH_ABBR = re.compile(
    r"\b([0-3]\d)[/\- ]([A-Za-zÁÉÍÓÚÑñ]{3,4})[/\- ](\d{4})(?:\s*[-–]?\s*([0-2]\d:[0-5]\d)(?:\s*h)?)?\b"
)

# Dinero: admite entero o decimal, con o sin símbolo, separadores de miles . o ,
#  - Capturamos el número, ignorando basura no-numérica al final (p.ej., "ºº")
_RE_MONEY_TOKEN = re.compile(
    r"\$?\s*([0-9]{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|[0-9]+(?:[.,]\d{2})?)"
)

# Línea “limpia” (solo monto, con o sin $); útil como fallback
_RE_MONEY_LINE = re.compile(
    r"^\s*\$?\s*([0-9]{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|[0-9]+(?:[.,]\d{2})?)\s*$",
    re.MULTILINE
)

# CBU/CVU (22 dígitos)
_RE_22DIG = re.compile(r"\b(\d{22})\b")

# Encabezados
_RE_TIT_ENVIASTE = re.compile(r"^\s*enviaste\s*$", re.IGNORECASE | re.MULTILINE)
_RE_TIT_CUENTA_DESTINO = re.compile(r"^\s*cuenta\s+destino\s*$", re.IGNORECASE | re.MULTILINE)
_RE_LABEL_CVU = re.compile(r"^\s*cvu\s*$", re.IGNORECASE | re.MULTILINE)
_RE_LABEL_CBU = re.compile(r"^\s*cbu\s*$", re.IGNORECASE | re.MULTILINE)

# Ventanas (en líneas) desde títulos
AMOUNT_WINDOW = 5
DEST_WINDOW = 10


def _split_lines(text: str) -> List[str]:
    """Devuelve líneas no vacías, recortadas."""
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]


def _to_float_money(token: str) -> float:
    """
    Convierte token de dinero (entero o decimal) a float.
    Heurística:
      - Si el último separador es coma, interpretamos coma decimal (formato AR).
      - Si el último separador es punto, interpretamos punto decimal (formato US).
      - Si no hay separador decimal, es entero.
    """
    s = token.strip()
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")
    if last_comma > last_dot:
        # AR: quitar puntos de miles y usar coma como decimal
        return float(s.replace(".", "").replace(",", "."))
    # US o entero con puntos de miles
    if last_dot > -1 and (len(s) - last_dot - 1) == 2:
        # decimal con punto
        return float(s.replace(",", ""))
    # entero (o miles con separadores)
    return float(s.replace(".", "").replace(",", ""))


def _iso_from_day_monthabbr_year(d: str, mon: str, y: str) -> str:
    """Normaliza 'DD/MES/AAAA' a 'YYYY-MM-DD' usando abreviatura de mes."""
    m = _MONTHS.get(mon.lower())
    if not m:
        # Intentar sin tildes ni eñes (por seguridad)
        m = _MONTHS.get(mon.lower().replace("ñ", "n").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u"))
    if not m:
        raise ExtractionError(f"Mes no reconocido: {mon}")
    return date(int(y), int(m), int(d)).isoformat()


# ───────────────────────────────────────────────────────────────────────────────
# Extracción: FECHA
# ───────────────────────────────────────────────────────────────────────────────

def _extract_fecha_iso(txt: str) -> str:
    """
    Busca la primera fecha con abreviatura de mes (DD/<MES>/YYYY).
    Si hay múltiples fechas distintas → ambigüedad.
    """
    candidates = []
    for m in _RE_DATE_MONTH_ABBR.finditer(txt):
        d, mon, y = m.group(1), m.group(2), m.group(3)
        try:
            iso = _iso_from_day_monthabbr_year(d, mon, y)
            candidates.append(iso)
        except Exception:
            continue

    if not candidates:
        raise ExtractionError("No se encontró una fecha válida con mes abreviado (p. ej., 02/JUL/2025).")

    uniq = sorted(set(candidates))
    if len(uniq) == 1:
        return uniq[0]
    raise ExtractionError(f"Ambigüedad: múltiples fechas detectadas {uniq}.")


# ───────────────────────────────────────────────────────────────────────────────
# Extracción: MONTO (prioriza ventana “Enviaste”)
# ───────────────────────────────────────────────────────────────────────────────

def _extract_monto(txt: str) -> float:
    """
    Preferencia:
      1) Desde 'Enviaste': buscar monto anclado con '$' en las AMOUNT_WINDOW líneas siguientes.
         - Si hay >1 montos distintos con '$' → ambigüedad.
      2) Desde 'Enviaste': si no hay '$', tomar el único token monetario cuyo valor >= 1.0
         en la ventana (ignorar '00', '0', etc.). Si >1 distintos → ambigüedad.
      3) Línea limpia con solo monto.
      4) Único token global.
    """
    lines = _split_lines(txt)

    tit_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"enviaste", ln, flags=re.IGNORECASE)]
    if tit_idxs:
        # 1) buscar con '$' en la ventana
        dollar_amounts = []
        for idx in tit_idxs:
            window_lines = lines[idx : min(len(lines), idx + AMOUNT_WINDOW + 1)]
            window = "\n".join(window_lines)
            # patrón que requiere '$' antes del número
            for m in re.finditer(r"\$\s*([0-9]{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|[0-9]+(?:[.,]\d{2})?)", window):
                dollar_amounts.append(m.group(1))
        if dollar_amounts:
            uniq = sorted(set(dollar_amounts))
            if len(uniq) == 1:
                return _to_float_money(uniq[0])
            raise ExtractionError("Ambigüedad: múltiples montos distintos con '$' cerca de 'Enviaste'.")

        # 2) sin '$': tomar tokens >= 1.0 (ignorar '00', '0', etc.)
        tokens = []
        for idx in tit_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + AMOUNT_WINDOW + 1)])
            tokens.extend(_RE_MONEY_TOKEN.findall(window))
        if tokens:
            # filtrar tokens menores a 1.0
            nums = sorted(set(t for t in tokens if _to_float_money(t) >= 1.0))
            if len(nums) == 1:
                return _to_float_money(nums[0])
            if len(nums) > 1:
                raise ExtractionError("Ambigüedad: múltiples montos (>=1) cerca de 'Enviaste'.")

    # 3) Línea limpia
    line_matches = _RE_MONEY_LINE.findall(txt)
    if len(line_matches) == 1:
        return _to_float_money(line_matches[0])
    if len(line_matches) > 1:
        raise ExtractionError("Ambigüedad: múltiples líneas con solo un monto.")

    # 4) Tokens globales
    tokens = _RE_MONEY_TOKEN.findall(txt)
    if not tokens:
        raise ExtractionError("No se encontró monto en el comprobante.")
    uniq_tokens = sorted(set(tokens))
    if len(uniq_tokens) == 1:
        return _to_float_money(uniq_tokens[0])
    raise ExtractionError(f"Ambigüedad: múltiples montos distintos detectados ({', '.join(uniq_tokens[:3])}).")


# ───────────────────────────────────────────────────────────────────────────────
# Extracción: CBU/CVU del DESTINO
# ───────────────────────────────────────────────────────────────────────────────

def _extract_cbu_cvu_destino(txt: str) -> Optional[str]:
    """
    Preferencia:
      1) Dentro del bloque 'Cuenta destino', buscar primero líneas con etiqueta 'CVU' o 'CBU'
         y tomar el 22-dígitos más cercano en las siguientes líneas de la ventana.
         Si aparecen múltiples candidatos distintos → ambigüedad.
      2) Fallback: único 22-dígitos global en todo el texto (estricto).
    """
    lines = _split_lines(txt)
    dest_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"cuenta\s+destino", ln, flags=re.IGNORECASE)]
    if dest_idxs:
        candidates: List[str] = []
        for idx in dest_idxs:
            # ventana limitada del bloque destino
            block = lines[idx : min(len(lines), idx + DEST_WINDOW + 1)]
            block_text = "\n".join(block)

            # Si hay etiquetas explícitas, busquemos el número “cerca”
            # CVU → suele venir el número en la misma línea o una de las siguientes
            label_positions = [j for j, ln in enumerate(block) if re.fullmatch(r"cvu", ln, flags=re.IGNORECASE)]
            label_positions += [j for j, ln in enumerate(block) if re.fullmatch(r"cbu", ln, flags=re.IGNORECASE)]
            if label_positions:
                for j in label_positions:
                    seg = "\n".join(block[j : min(len(block), j + 4)])  # 3 líneas después del label
                    candidates.extend(_RE_22DIG.findall(seg))

            # Además, por seguridad, capturar cualquier 22 dígitos en el bloque
            candidates.extend(_RE_22DIG.findall(block_text))

        uniq = sorted(set(candidates))
        if len(uniq) == 1:
            return uniq[0]
        if len(uniq) > 1:
            raise ExtractionError("Ambigüedad: múltiples CBU/CVU detectados en 'Cuenta destino'.")

    # Fallback: único 22 dígitos global
    all_nums = _RE_22DIG.findall(txt)
    uniq_all = sorted(set(all_nums))
    if len(uniq_all) == 1:
        return uniq_all[0]
    if len(uniq_all) > 1:
        raise ExtractionError("Ambigüedad: múltiples CBU/CVU (22 dígitos) en el comprobante.")

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
    cbu_cvu = _extract_cbu_cvu_destino(txt)

    result = ParseResult(monto=monto, fecha=fecha_iso, cbu=cbu_cvu, alias=None)

    # Validación de negocio (exact match con lo esperado)
    validate_all_expected(
        result,
        expected_amount=cfg["monto"],
        expected_date_iso=cfg["fecha"],
        expected_cbu=cfg.get("cbu"),      # puede ser CBU o CVU; comparamos contra lo esperado
        expected_alias=cfg.get("alias"),
    )

    return dict(monto=result.monto, fecha=result.fecha, cbu=result.cbu, alias=result.alias)
