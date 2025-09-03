"""
Extractor robusto para comprobantes de Banco Macro.

Patrones habituales:
- Marca: "Banco Macro", "Macro"
- Encabezados: "Transferencia a terceros", "Fecha y hora", "Importe", "CBU/CVU destino"
- Fecha/hora: puede venir como "02:33 PM 04/07/2025" (hora antes de la fecha) o similar.
- Importe: "US-like" ($ 2,420,000.00) o "AR-like" ($ 2.420.000,00).
- Destino: etiqueta "CBU/CVU destino" seguida del número (22 dígitos).

Estrategia (estricta con fallbacks controlados):
- `matches`: busca "macro" y/o "banco macro".
- `fecha`: prioriza bloque "Fecha y hora" y extrae la *fecha* (ignora la hora).
          Fallback: única fecha DD/MM/YYYY en todo el texto.
- `monto`: prioriza ventana desde "Importe"; fallback línea limpia; fallback único token global.
- `destino`: prioriza ventana desde "CBU/CVU destino"; fallback único 22 dígitos global.
- `alias`: no suele imprimirse en Macro → devolvemos None.

Salida:
- dict(monto: float, fecha: 'YYYY-MM-DD', cbu: str|None, alias: None)
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

_MACRO_PRIMARY = ("banco macro", " macro ")  # incluir espacio para evitar falso positivo en palabras compuestas
_MACRO_SECONDARY = ("transferencia a terceros", "fecha y hora", "cbu/cvu destino", "importe")

def matches(texto: str) -> bool:
    """
    True si el OCR contiene señales claras de Banco Macro.
    Requiere "banco macro" o ' macro ' (con espacios) y, preferentemente, alguna secundaria.
    """
    t = f" { (texto or '').lower() } "
    if not any(k in t for k in _MACRO_PRIMARY):
        return False
    return any(k.strip() in t for k in _MACRO_SECONDARY)


# ───────────────────────────────────────────────────────────────────────────────
# Regex y utilidades
# ───────────────────────────────────────────────────────────────────────────────

# Tokens monetarios (AR y US). Permitimos miles con punto o coma y decimales con coma o punto.
_RE_MONEY_TOKEN = re.compile(
    r"\$?\s*("                                # grupo 1 = número
    r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)"  # miles + opcionales decimales
    r"|"
    r"(?:\d+(?:[.,]\d{2})?)"                    # entero simple o con decimales
    r")"
)
# Línea “limpia” con solo monto (reduce falsos positivos)
_RE_MONEY_LINE = re.compile(
    r"^\s*\$?\s*("
    r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)"
    r"|"
    r"(?:\d+(?:[.,]\d{2})?)"
    r")\s*$",
    re.MULTILINE
)

# Fecha: DD/MM/YYYY (con separadores / o -)
_RE_DATE_DMY = re.compile(r"\b([0-3]\d)[/\-]([0-1]\d)[/\-](\d{4})\b")

# En "Fecha y hora" a veces la hora figura ANTES de la fecha, p. ej. "02:33 PM 04/07/2025".
# Capturamos la fecha aunque haya una hora AM/PM alrededor.
_RE_TIME_AMPM = re.compile(r"\b(0?[1-9]|1[0-2]):([0-5]\d)\s*(AM|PM)\b", re.IGNORECASE)

# CBU/CVU (22 dígitos)
_RE_22DIG = re.compile(r"\b(\d{22})\b")

# Encabezados / etiquetas
_RE_TIT_FECHA_HORA   = re.compile(r"^\s*fecha\s+y\s+hora\s*$", re.IGNORECASE | re.MULTILINE)
_RE_TIT_IMPORTE      = re.compile(r"^\s*importe\s*$", re.IGNORECASE | re.MULTILINE)
_RE_TIT_CBU_DESTINO  = re.compile(r"^\s*cbu/cvu\s+destino\s*$", re.IGNORECASE | re.MULTILINE)

# Ventanas (en líneas) desde títulos
FECHA_WINDOW = 4
IMPORTE_WINDOW = 6
DESTINO_WINDOW = 6


def _split_lines(text: str) -> List[str]:
    """Devuelve líneas no vacías y recortadas."""
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]


def _to_float_money(token: str) -> float:
    """
    Convierte token monetario a float.
    Heurística:
      - Si el último separador visible es coma → coma decimal (AR).
      - Si el último separador visible es punto con 2 decimales → punto decimal (US).
      - Si no hay decimales → entero (remueve separadores de miles).
    """
    s = token.strip()
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")
    if last_comma > last_dot:
        return float(s.replace(".", "").replace(",", "."))
    if last_dot > -1 and (len(s) - last_dot - 1) == 2:
        return float(s.replace(",", ""))
    return float(s.replace(".", "").replace(",", ""))


def _iso_from_dmy(d: str, m: str, y: str) -> str:
    """Convierte DD/MM/YYYY a YYYY-MM-DD (valida)."""
    dt = datetime(year=int(y), month=int(m), day=int(d)).date()
    return dt.isoformat()


# ───────────────────────────────────────────────────────────────────────────────
# Extracción de campos
# ───────────────────────────────────────────────────────────────────────────────

def _extract_fecha_iso(txt: str) -> str:
    """
    Preferencia:
      1) Ventana desde "Fecha y hora": tomar la ÚNICA fecha DD/MM/YYYY en FECHA_WINDOW líneas
         (la hora puede estar en la misma línea o en la anterior, no afecta; devolvemos SOLO la fecha).
      2) Fallback: fecha única global DD/MM/YYYY.
    Ambigüedad → error.
    """
    lines = _split_lines(txt)

    tit_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"fecha\s+y\s+hora", ln, flags=re.IGNORECASE)]
    if tit_idxs:
        candidates = []
        for idx in tit_idxs:
            # tomamos desde la línea del título hacia unas pocas líneas abajo
            start = idx
            end = min(len(lines), idx + FECHA_WINDOW + 1)
            window = "\n".join(lines[start:end])
            for m in _RE_DATE_DMY.finditer(window):
                candidates.append(_iso_from_dmy(m.group(1), m.group(2), m.group(3)))
        uniq = sorted(set(candidates))
        if len(uniq) == 1:
            return uniq[0]
        if len(uniq) > 1:
            raise ExtractionError(f"Ambigüedad: múltiples fechas cerca de 'Fecha y hora' {uniq}.")

    # Fallback: única fecha global
    all_dates = [_iso_from_dmy(m.group(1), m.group(2), m.group(3)) for m in _RE_DATE_DMY.finditer(txt)]
    if not all_dates:
        raise ExtractionError("No se encontró una fecha válida.")
    uniq_all = sorted(set(all_dates))
    if len(uniq_all) == 1:
        return uniq_all[0]
    raise ExtractionError(f"Ambigüedad: múltiples fechas detectadas {uniq_all}.")


def _is_plain_big_integer(token: str, *, min_len: int = 7) -> bool:
    """
    True si el token es un entero sin separadores ni decimales, y con longitud >= min_len.
    Sirve para descartar referencias/cuentas como '351409420892947'.
    """
    s = token.strip()
    if "." in s or "," in s:
        return False
    return s.isdigit() and len(s) >= min_len


def _extract_monto(txt: str) -> float:
    """
    Preferencia:
      1) Ventana desde 'Importe': montos con '$' → filtra enteros grandes planos → desambigua por valor.
      2) Si no hay '$': tokens monetarios en ventana filtrando enteros grandes → desambigua por valor.
      3) Línea 'monto-only' global → desambigua por valor.
      4) Tokens globales → desambigua por valor.
    """
    lines = _split_lines(txt)

    # 1) Ventana desde "Importe"
    tit_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"importe", ln, re.IGNORECASE)]
    if tit_idxs:
        # 1.a) Preferir montos con '$'
        dollar = []
        for idx in tit_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + IMPORTE_WINDOW + 1)])
            for m in re.finditer(
                r"\$\s*("  # número
                r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)|(?:\d+(?:[.,]\d{2})?)"
                r")",
                window,
            ):
                t = m.group(1)
                if not _is_plain_big_integer(t):
                    dollar.append(t)
        if dollar:
            uniq_vals = sorted({ _to_float_money(t) for t in dollar })
            if len(uniq_vals) == 1:
                return uniq_vals[0]
            raise ExtractionError("Ambigüedad: múltiples montos distintos con '$' cerca de 'Importe'.")

        # 1.b) Sin '$': tokens monetarios pero filtrando enteros grandes
        near = []
        for idx in tit_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + IMPORTE_WINDOW + 1)])
            for t in _RE_MONEY_TOKEN.findall(window):
                if not _is_plain_big_integer(t):
                    near.append(t)
        if near:
            uniq_vals = sorted({ _to_float_money(t) for t in near })
            if len(uniq_vals) == 1:
                return uniq_vals[0]
            raise ExtractionError("Ambigüedad: múltiples montos distintos cerca de 'Importe'.")

    # 2) Línea 'monto-only' global
    lm = _RE_MONEY_LINE.findall(txt)
    if lm:
        uniq_vals = sorted({ _to_float_money(t) for t in lm if not _is_plain_big_integer(t) })
        if len(uniq_vals) == 1:
            return uniq_vals[0]
        if len(uniq_vals) > 1:
            raise ExtractionError("Ambigüedad: múltiples líneas con solo un monto.")

    # 3) Tokens globales
    tokens = [t for t in _RE_MONEY_TOKEN.findall(txt) if not _is_plain_big_integer(t)]
    if not tokens:
        raise ExtractionError("No se encontró monto en el comprobante.")
    uniq_vals = sorted({ _to_float_money(t) for t in tokens })
    if len(uniq_vals) == 1:
        return uniq_vals[0]
    raise ExtractionError("Ambigüedad: múltiples montos distintos detectados.")


def _extract_cbu_destino(txt: str) -> Optional[str]:
    """
    Preferencia:
      1) Ventana desde "CBU/CVU destino": tomar el ÚNICO 22 dígitos en DESTINO_WINDOW líneas.
      2) Fallback: único 22 dígitos global.
    Ambigüedad → error.
    """
    lines = _split_lines(txt)

    tit_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"cbu/cvu\s+destino", ln, flags=re.IGNORECASE)]
    if tit_idxs:
        candidates = []
        for idx in tit_idxs:
            start = idx
            end = min(len(lines), idx + DESTINO_WINDOW + 1)
            window = "\n".join(lines[start:end])
            candidates.extend(_RE_22DIG.findall(window))
        uniq = sorted(set(candidates))
        if len(uniq) == 1:
            return uniq[0]
        if len(uniq) > 1:
            raise ExtractionError("Ambigüedad: múltiples CBU/CVU en 'CBU/CVU destino'.")

    # Fallback: único global
    all_22 = _RE_22DIG.findall(txt)
    uniq_all = sorted(set(all_22))
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
    """
    if not texto:
        raise ExtractionError("Texto vacío.")

    txt = normalize_text_keep_lines(texto)

    fecha_iso = _extract_fecha_iso(txt)
    monto = _extract_monto(txt)
    cbu = _extract_cbu_destino(txt)

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
