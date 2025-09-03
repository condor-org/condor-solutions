"""
Base común para extractores de comprobantes por banco.

Enfoque:
- Cada banco PARSEA su layout con sus regex (en banks/<banco>.py).
- Este módulo NO busca montos/fechas/CBU en el texto.
- Provee utilidades para:
  * Normalizar texto OCR.
  * Estandarizar errores (ExtractionError).
  * Validar que lo extraído por el banco coincide EXACTO con lo esperado.
  * Loguear datos de forma consistente.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────────
# Excepción estándar
# ───────────────────────────────────────────────────────────────────────────────

class ExtractionError(Exception):
    """Fallo en extracción o validación de datos del comprobante."""
    pass


# ───────────────────────────────────────────────────────────────────────────────
# Modelo de salida CONSISTENTE entre bancos
# ───────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ParseResult:
    """
    Lo que debe devolver cualquier extractor por banco:

    - monto: float           (ej. 1234.56)
    - fecha: str             ('YYYY-MM-DD')
    - cbu: Optional[str]     (22 dígitos exactos si aplica)
    - alias: Optional[str]   (si aplica)
    """
    monto: float
    fecha: str
    cbu: Optional[str] = None
    alias: Optional[str] = None


# ───────────────────────────────────────────────────────────────────────────────
# Normalización de texto OCR (ayuda a que regex del banco sean más estables)
# ───────────────────────────────────────────────────────────────────────────────

def normalize_text_keep_lines(text: str) -> str:
    """
    Limpia el texto manteniendo saltos de línea, para regex por “layout”:
    - Reemplaza tabs por espacio
    - Colapsa espacios múltiples (sin tocar '\n')
    - Recorta espacios a izquierda/derecha de cada línea
    - Devuelve el string final sin espacios extra en extremos
    """
    if not text:
        return ""
    t = text.replace("\t", " ")
    t = re.sub(r"[ ]{2,}", " ", t)
    t = "\n".join(s.strip() for s in t.splitlines())
    return t.strip()


# ───────────────────────────────────────────────────────────────────────────────
# Validadores de NEGOCIO (comparan lo ya parseado por el banco)
# ───────────────────────────────────────────────────────────────────────────────

def validate_expected_amount(parsed_amount: float, expected_amount: float) -> None:
    """
    Verifica que el monto parseado por el extractor del banco
    sea EXACTAMENTE igual al esperado (redondeo a 2 decimales).
    """
    if expected_amount is None:
        raise ExtractionError("Falta monto esperado para validación.")
    if round(parsed_amount, 2) != round(expected_amount, 2):
        raise ExtractionError(
            f"Monto no coincide: detectado={parsed_amount:.2f}, esperado={expected_amount:.2f}"
        )

def validate_expected_date(parsed_date_iso: str, expected_date_iso: str) -> None:
    """
    Verifica que la fecha parseada por el extractor del banco
    sea EXACTAMENTE igual a la esperada (formato 'YYYY-MM-DD').
    """
    if not expected_date_iso:
        raise ExtractionError("Falta fecha esperada para validación.")
    if parsed_date_iso != expected_date_iso:
        raise ExtractionError(
            f"Fecha no coincide: detectada={parsed_date_iso}, esperada={expected_date_iso}"
        )

def validate_expected_destination(
    parsed_cbu: Optional[str],
    parsed_alias: Optional[str],
    *,
    expected_cbu: Optional[str],
    expected_alias: Optional[str],
) -> None:
    """
    Verifica que el destino (CBU o alias) coincida EXACTO con lo esperado.
    Regla:
      - Si ambos esperados vienen, alcanza con que coincida alguno.
      - Si sólo viene CBU esperado, debe coincidir CBU.
      - Si sólo viene Alias esperado, debe coincidir Alias.
      - Si no viene ninguno esperado, no valida (se acepta lo parseado).
    """
    # Normalizar CBU esperado (quitar no-dígitos)
    if expected_cbu:
        exp_cbu = re.sub(r"\D", "", expected_cbu)
    else:
        exp_cbu = None

    ok_cbu = bool(exp_cbu and parsed_cbu and parsed_cbu == exp_cbu)
    ok_alias = bool(
        expected_alias and parsed_alias and parsed_alias.lower() == expected_alias.lower()
    )

    if expected_cbu and expected_alias:
        if not (ok_cbu or ok_alias):
            raise ExtractionError("Destino no coincide ni por CBU ni por alias.")
    elif expected_cbu:
        if not ok_cbu:
            raise ExtractionError("CBU no coincide.")
    elif expected_alias:
        if not ok_alias:
            raise ExtractionError("Alias no coincide.")
    else:
        # Nada que validar; se acepta tal cual
        logger.info("[DESTINO] Sin esperado; se acepta el destino detectado.")


def validate_all_expected(
    result: ParseResult,
    *,
    expected_amount: float,
    expected_date_iso: str,
    expected_cbu: Optional[str],
    expected_alias: Optional[str],
) -> ParseResult:
    """
    Valida TODO contra lo esperado usando las funciones anteriores.
    Devuelve el mismo ParseResult si pasa todas las validaciones.
    Lanza ExtractionError en el primer fallo.
    """
    validate_expected_amount(result.monto, expected_amount)
    validate_expected_date(result.fecha, expected_date_iso)
    validate_expected_destination(
        result.cbu, result.alias, expected_cbu=expected_cbu, expected_alias=expected_alias
    )
    return result
