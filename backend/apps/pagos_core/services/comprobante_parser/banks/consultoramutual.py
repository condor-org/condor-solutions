"""
Extractor robusto para comprobantes de Consultora Mutual.

Patrones típicos (ejemplo real):
  CONSULTORA
  MUTUAL
  Fecha y hora:
  10/07/2025 13:20
  Nro operación:
  ...
  Cuenta origen: ...
  Monto: $882000,00
  Moneda: ARS
  DATOS DEL DESTINATARIO
  Nombre: ...
  CBU/Alias: 0720049688000000861818
  ...

Estrategia:
- Detección por palabras clave (“consultora”, “mutual”, “coelsa id”).
- Fecha: prioriza la etiqueta “Fecha y hora:” con formato DD/MM/YYYY (ignora la hora).
- Monto: prioriza la etiqueta “Monto:” con formato AR estricto (1.234,56 o 882000,00).
- CBU/Alias: busca dentro del bloque “DATOS DEL DESTINATARIO”; si falta, usa la etiqueta “CBU/Alias:” en todo el texto; último recurso: único CBU global (22 dígitos).
- Estricto: múltiples candidatos para un mismo campo ⇒ ExtractionError.

Salida:
- dict(monto: float, fecha: 'YYYY-MM-DD', cbu: str|None, alias: str|None)

Validación:
- Compara con lo esperado (monto/fecha/cbu/alias) usando validate_all_expected.
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

_CM_PRIMARY = ("consultora", "mutual")
_CM_SECONDARY = ("coelsa id", "datos del destinatario", "comprobante", "nro operación", "monto:")

def matches(texto: str) -> bool:
    """
    Devuelve True si el OCR contiene señales claras de Consultora Mutual.
    Requiere al menos una palabra primaria (“consultora” / “mutual”) y alguna secundaria.
    """
    t = (texto or "").lower()
    if not any(k in t for k in _CM_PRIMARY):
        return False
    return any(k in t for k in _CM_SECONDARY)


# ───────────────────────────────────────────────────────────────────────────────
# Regex base (monto / fecha / cbu/alias) y utilidades
# ───────────────────────────────────────────────────────────────────────────────

# Fecha con etiqueta "Fecha y hora:" (DD/MM/YYYY, con hora opcional)
_RE_FECHA_ETIQUETA = re.compile(
    r"fecha\s+y\s+hora:\s*([0-3]\d/[0-1]\d/\d{4})(?:\s+[0-2]\d:[0-5]\d(?::[0-5]\d)?)?",
    re.IGNORECASE
)
# Fecha general (fallback)
_RE_FECHA_DDMMYYYY = re.compile(r"\b([0-3]\d)/([0-1]\d)/(\d{4})\b")

# Monto con etiqueta "Monto:" (línea propia)
# Acepta $ opcional, miles con punto, decimales con coma; o sin miles (882000,00)
_RE_MONTO_ETIQUETA = re.compile(
    r"^\s*monto:\s*\$?\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]+,[0-9]{2})\s*$",
    re.IGNORECASE | re.MULTILINE
)

# Tokens de dinero (fallback muy conservador)
_RE_MONEY_TOKEN = re.compile(r"\$?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})")

# CBU/Alias con etiqueta
_RE_CBU_ALIAS_LABEL = re.compile(
    r"cbu/alias:\s*([0-9]{22}|[A-Za-z0-9](?:[A-Za-z0-9\.]{4,18})[A-Za-z0-9])",
    re.IGNORECASE
)
# CBU crudo (22 dígitos)
_RE_CBU_22 = re.compile(r"\b(\d{22})\b")
# Alias estricto (6–20, alfanumérico y puntos, no empezar/terminar con '.')
_RE_ALIAS = re.compile(r"\b([A-Za-z0-9](?:[A-Za-z0-9\.]{4,18})[A-Za-z0-9])\b")

# Encabezado de bloque destino
_RE_TIT_DEST = re.compile(r"^\s*datos\s+del\s+destinatario\s*$", re.IGNORECASE | re.MULTILINE)

# Ventana en líneas desde el título de destino
DEST_WINDOW = 10


def _split_lines(text: str) -> List[str]:
    """Normaliza y devuelve líneas no vacías (para búsquedas por bloque)."""
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]


def _to_float_ar(num_str: str) -> float:
    """Convierte '1.234,56' o '882000,00' a 1234.56 o 882000.00."""
    s = num_str.replace(".", "").replace(",", ".")
    return float(s)


def _iso_from_ddmmyyyy(s: str) -> str:
    """Convierte 'DD/MM/YYYY' a 'YYYY-MM-DD' (+ valida)."""
    dt = datetime.strptime(s, "%d/%m/%Y").date()
    return dt.isoformat()


# ───────────────────────────────────────────────────────────────────────────────
# Extractores de campo (estrictos con escalera de fallbacks)
# ───────────────────────────────────────────────────────────────────────────────

def _extract_fecha_iso(txt: str) -> str:
    """
    Preferencia:
      1) 'Fecha y hora:' → tomar la fecha (ignora hora).
      2) Fallback: única fecha DD/MM/YYYY en todo el documento.
    Ambigüedad → error.
    """
    m = _RE_FECHA_ETIQUETA.search(txt)
    if m:
        return _iso_from_ddmmyyyy(m.group(1))

    # Fallback: buscar todas las fechas DD/MM/YYYY
    all_dates = [_iso_from_ddmmyyyy(m.group(0)) for m in _RE_FECHA_DDMMYYYY.finditer(txt)]
    if not all_dates:
        raise ExtractionError("No se encontró una fecha válida.")
    uniq = sorted(set(all_dates))
    if len(uniq) > 1:
        raise ExtractionError(f"Ambigüedad: múltiples fechas detectadas {uniq}.")
    return uniq[0]


def _extract_monto(txt: str) -> float:
    """
    Preferencia:
      1) Línea etiquetada 'Monto:' (única).
      2) Fallback: único token de dinero en todo el texto o el mismo repetido.
    Ambigüedad → error.
    """
    montos = _RE_MONTO_ETIQUETA.findall(txt)
    if len(montos) == 1:
        return _to_float_ar(montos[0])
    if len(montos) > 1:
        raise ExtractionError("Ambigüedad: múltiples montos en líneas 'Monto:'.")

    tokens = _RE_MONEY_TOKEN.findall(txt)
    if not tokens:
        raise ExtractionError("No se encontró monto en el comprobante.")
    uniq = {t for t in tokens}
    if len(uniq) == 1:
        return _to_float_ar(tokens[0])
    raise ExtractionError(f"Ambigüedad: múltiples montos distintos detectados ({', '.join(list(uniq)[:3])}).")


def _extract_destino(txt: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extrae CBU o Alias del destinatario.

    Preferencia:
      1) Dentro del bloque 'DATOS DEL DESTINATARIO' tomar:
         - 'CBU/Alias:' (22 dígitos o alias estricto), o
         - primer CBU de 22 dígitos que aparezca.
         Si hay >1 en la ventana → ambigüedad.
      2) Fallback: buscar 'CBU/Alias:' en todo el documento.
      3) Último recurso: único CBU global (22 dígitos).
    """
    # 1) Bloque 'DATOS DEL DESTINATARIO'
    lines = _split_lines(txt)
    dest_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"datos\s+del\s+destinatario", ln, flags=re.IGNORECASE)]
    if dest_idxs:
        candidates_cbu = []
        candidates_alias = []
        for idx in dest_idxs:
            window = "\n".join(lines[idx : min(len(lines), idx + DEST_WINDOW + 1)])
            # Etiqueta compuesta
            m = _RE_CBU_ALIAS_LABEL.search(window)
            if m:
                token = m.group(1)
                if token.isdigit() and len(token) == 22:
                    candidates_cbu.append(token)
                else:
                    candidates_alias.append(token)
            # CBU crudo en la ventana
            candidates_cbu.extend(_RE_CBU_22.findall(window))

        uniq_cbu = sorted(set(candidates_cbu))
        uniq_alias = sorted(set(candidates_alias))

        if len(uniq_cbu) + len(uniq_alias) == 0:
            # seguimos a fallbacks
            pass
        elif len(uniq_cbu) + len(uniq_alias) == 1:
            return (uniq_cbu[0] if uniq_cbu else None, uniq_alias[0] if uniq_alias else None)
        else:
            raise ExtractionError("Ambigüedad: múltiples destinos en 'DATOS DEL DESTINATARIO'.")

    # 2) Fallback: etiqueta en todo el documento
    m2 = _RE_CBU_ALIAS_LABEL.search(txt)
    if m2:
        token = m2.group(1)
        if token.isdigit() and len(token) == 22:
            return (token, None)
        return (None, token)

    # 3) Único CBU global
    all_cbu = _RE_CBU_22.findall(txt)
    uniq_all = sorted(set(all_cbu))
    if len(uniq_all) == 1:
        return (uniq_all[0], None)
    if len(uniq_all) > 1:
        raise ExtractionError("Ambigüedad: múltiples CBU (22 dígitos) en el comprobante.")

    # Puede no venir destino (poco probable en este layout)
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

    Errores:
      - ExtractionError ante ambigüedades o faltantes.
    """
    if not texto:
        raise ExtractionError("Texto vacío.")

    txt = normalize_text_keep_lines(texto)

    fecha_iso = _extract_fecha_iso(txt)
    monto = _extract_monto(txt)
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
