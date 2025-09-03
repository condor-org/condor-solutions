"""
Extractor robusto para comprobantes de QuikiPay / QUIKI Pay.

Patrones observados:
- Encabezados: "QUIKI", "QuikiPay", "Aviso de transferencia"
- Bloques: "Origen", "Beneficiario"
- Etiquetas: "CBU/CVU", "Importe", "Fecha y Hora", "Trx.#", "Referencia", "Detalle"
- Fechas: 'YYYY-MM-DD HH:MM(:SS)?' (frecuente) o 'DD/MM/YYYY'
- Monto: línea cerca de "Importe" (a veces inmediatamente debajo o pocas líneas después)

Estrategia (estricta con fallbacks):
- Detección: keywords de marca.
- Monto: ventana alrededor de "Importe" (hacia abajo y, si hace falta, 2 líneas hacia arriba);
         si no, línea “limpia”; último recurso: único token monetario global (o el mismo repetido).
- Fecha: (0) ventana específica “Fecha y Hora” con patrón estricto,
         (1) ISO flexible (raw y normalizado),
         (2) split de tokens,
         (3) ISO date-only,
         (4) DD/MM/YYYY.
- CBU/CVU de DESTINO (anti-ambigüedad):
         1) label 'CBU/CVU' dentro de Beneficiario → primer 22 dígitos en las 3–5 líneas siguientes;
         2) si hay cfg['cbu'], usarlo si está presente;
         3) remover los 22 dígitos que estén en ORIGEN;
         4) elegir el más cercano al label en Beneficiario;
         5) si persiste empate, tomar el último 22 dígitos del documento;
         6) si no hay, None.

Salida:
- dict(monto: float, fecha: 'YYYY-MM-DD', cbu: str|None, alias: None)
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

_QP_PRIMARY = ("quikipay", "quiki pay", "quiki")
_QP_SECONDARY = ("aviso de transferencia", "cbu/cvu", "beneficiario", "trx.#", "fecha y hora", "importe")

def matches(texto: str) -> bool:
    t = (texto or "").lower()
    if not any(k in t for k in _QP_PRIMARY):
        return False
    return any(k in t for k in _QP_SECONDARY)

# ───────────────────────────────────────────────────────────────────────────────
# Regex y utilidades
# ───────────────────────────────────────────────────────────────────────────────

_RE_MONEY_TOKEN = re.compile(r"\$?\s*((?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)|(?:\d+(?:[.,]\d{2})?))")
_RE_MONEY_LINE  = re.compile(r"^\s*\$?\s*((?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)|(?:\d+(?:[.,]\d{2})?))\s*$", re.MULTILINE)

# QuikiPay: fecha exacta en formato YYYY-MM-DD HH:MM:SS en ventana de "Fecha y Hora"
_RE_QP_ISO_LINE_STRICT = re.compile(r"\b(20\d{2}-[01]\d-[0-3]\d)\s+([01]\d|2[0-3]):[0-5]\d:[0-5]\d\b")

# ISO flexible (raw: cualquier separador no numérico, admite saltos de línea)
_RE_DT_ISO_RAW = re.compile(
    r"(20\d{2})\D+(1[0-2]|0[1-9])\D+(3[01]|0[1-9])\D+"
    r"(2[0-3]|[01]\d)\D+([0-5]\d)(?:\D+([0-5]\d))?",
    flags=re.DOTALL
)
# ISO flexible (normalizado)
_RE_DT_ISO_FLEX = re.compile(
    r"\b(20\d{2})[^\d\n]?(1[0-2]|0[1-9])[^\d\n]?(3[01]|0[1-9])[T\s]+"
    r"(2[0-3]|[01]\d)[^\d\n]?([0-5]\d)(?:[^\d\n]?([0-5]\d))?\b"
)

# Split tokens: YYYY MM DD HH mm [ss]
_RE_DT_SPLIT = re.compile(
    r"\b(20\d{2})\s+(1[0-2]|0[1-9])\s+(3[01]|0[1-9])\s+"
    r"(2[0-3]|[01]\d)\s+([0-5]\d)(?:\s+([0-5]\d))?\b"
)

# ISO date-only
_RE_DATE_ISO_ONLY = re.compile(r"\b(20\d{2})[^\d\n]?(1[0-2]|0[1-9])[^\d\n]?(3[01]|0[1-9])\b")

# DMY
_RE_DATE_DMY = re.compile(r"\b([0-3]\d)/([0-1]\d)/(\d{4})\b")

# 22 dígitos
_RE_22DIG = re.compile(r"\b(\d{22})\b")

# Ventanas
IMPORTE_WINDOW_DOWN = 6
IMPORTE_WINDOW_UP   = 2
BENEF_WINDOW_DOWN   = 14
FECHA_WINDOW_DOWN   = 4

def _split_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]

def _to_float_money(token: str) -> float:
    s = token.strip()
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")
    if last_comma > last_dot:
        return float(s.replace(".", "").replace(",", "."))
    if last_dot > -1 and (len(s) - last_dot - 1) == 2:
        return float(s.replace(",", ""))
    return float(s.replace(".", "").replace(",", ""))

def _iso_from_iso_datetime(m: re.Match) -> str:
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    dt = datetime(year=y, month=mo, day=d).date()
    return dt.isoformat()

def _iso_from_dmy(d: str, m: str, y: str) -> str:
    dt = datetime(year=int(y), month=int(m), day=int(d)).date()
    return dt.isoformat()

# ───────────────────────────────────────────────────────────────────────────────
# Extracción MONTO
# ───────────────────────────────────────────────────────────────────────────────

def _is_plain_big_integer(token: str, *, min_len: int = 7) -> bool:
    s = token.strip()
    if "." in s or "," in s:
        return False
    return s.isdigit() and len(s) >= min_len

def _extract_monto(txt: str) -> float:
    lines = _split_lines(txt)
    tit_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"importe", ln, flags=re.IGNORECASE)]
    if tit_idxs:
        dollar = []
        for idx in tit_idxs:
            window = "\n".join(lines[idx: min(len(lines), idx + IMPORTE_WINDOW_DOWN + 1)])
            for m in re.finditer(r"\$\s*((?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?)|(?:\d+(?:[.,]\d{2})?))", window):
                t = m.group(1)
                if not _is_plain_big_integer(t):
                    dollar.append(t)
        if dollar:
            uniq_vals = sorted({_to_float_money(t) for t in dollar})
            if len(uniq_vals) == 1:
                return uniq_vals[0]
            raise ExtractionError("Ambigüedad: múltiples montos distintos con '$' cerca de 'Importe'.")

        near_tokens = []
        for idx in tit_idxs:
            window = "\n".join(lines[idx: min(len(lines), idx + IMPORTE_WINDOW_DOWN + 1)])
            for t in _RE_MONEY_TOKEN.findall(window):
                if _is_plain_big_integer(t):
                    continue
                if "." in t or "," in t:
                    near_tokens.append(t)
        if near_tokens:
            uniq_vals = sorted({_to_float_money(t) for t in near_tokens})
            if len(uniq_vals) == 1:
                return uniq_vals[0]
            raise ExtractionError("Ambigüedad: múltiples montos distintos cerca de 'Importe'.")

    lm = [t for t in _RE_MONEY_LINE.findall(txt) if not _is_plain_big_integer(t)]
    if lm:
        uniq_vals = sorted({_to_float_money(t) for t in lm})
        if len(uniq_vals) == 1:
            return uniq_vals[0]
        raise ExtractionError("Ambigüedad: múltiples líneas con solo un monto.")

    tokens = [t for t in _RE_MONEY_TOKEN.findall(txt) if not _is_plain_big_integer(t)]
    if not tokens:
        raise ExtractionError("No se encontró monto en el comprobante.")
    uniq_vals = sorted({_to_float_money(t) for t in tokens})
    if len(uniq_vals) == 1:
        return uniq_vals[0]
    raise ExtractionError("Ambigüedad: múltiples montos distintos detectados.")

# ───────────────────────────────────────────────────────────────────────────────
# Extracción FECHA
# ───────────────────────────────────────────────────────────────────────────────

def _extract_qp_fecha_en_ventana(texto: str, *, window_down: int = 4) -> Optional[str]:
    """Busca 'YYYY-MM-DD HH:MM:SS' en ventana posterior a 'Fecha y Hora'."""
    lines = _split_lines(texto)
    idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"fecha\s+y\s+hora", ln, flags=re.IGNORECASE)]
    for idx in idxs:
        block = lines[idx: min(len(lines), idx + window_down + 1)]
        for ln in block:
            m = _RE_QP_ISO_LINE_STRICT.search(ln)
            if m:
                return m.group(1)
        m = _RE_QP_ISO_LINE_STRICT.search("\n".join(block))
        if m:
            return m.group(1)
    return None

def _extract_fecha_iso(texto_crudo: str, txt_norm: str) -> str:
    # 0) QuikiPay: ventana "Fecha y Hora" con formato exacto
    qp_in_win = _extract_qp_fecha_en_ventana(texto_crudo)
    if qp_in_win:
        return qp_in_win
    qp_in_win_norm = _extract_qp_fecha_en_ventana(txt_norm)
    if qp_in_win_norm:
        return qp_in_win_norm

    # 1) RAW global
    iso_raw = list(_RE_DT_ISO_RAW.finditer(texto_crudo))
    if iso_raw:
        dates = {_iso_from_iso_datetime(m) for m in iso_raw}
        if len(dates) == 1:
            return next(iter(dates))

    # 2) Normalizado
    iso_flex = list(_RE_DT_ISO_FLEX.finditer(txt_norm))
    if iso_flex:
        dates = {_iso_from_iso_datetime(m) for m in iso_flex}
        if len(dates) == 1:
            return next(iter(dates))

    # 3) Split
    split = list(_RE_DT_SPLIT.finditer(texto_crudo)) or list(_RE_DT_SPLIT.finditer(txt_norm))
    if split:
        dates = {_iso_from_iso_datetime(m) for m in split}
        if len(dates) == 1:
            return next(iter(dates))

    # 4) ISO date-only
    d_iso = list(_RE_DATE_ISO_ONLY.finditer(texto_crudo)) or list(_RE_DATE_ISO_ONLY.finditer(txt_norm))
    if d_iso:
        dates = {_iso_from_iso_datetime(m) for m in d_iso}
        if len(dates) == 1:
            return next(iter(dates))

    # 5) DD/MM/YYYY
    dmy = [_iso_from_dmy(m.group(1), m.group(2), m.group(3)) for m in _RE_DATE_DMY.finditer(texto_crudo)]
    dmy = dmy or [_iso_from_dmy(m.group(1), m.group(2), m.group(3)) for m in _RE_DATE_DMY.finditer(txt_norm)]
    if dmy:
        uniq = sorted(set(dmy))
        if len(uniq) == 1:
            return uniq[0]

    raise ExtractionError("No se encontró una fecha válida.")

# ───────────────────────────────────────────────────────────────────────────────
# Extracción CBU/CVU (anti-ambigüedad)
# ───────────────────────────────────────────────────────────────────────────────

def _find_all_22_with_positions(lines: List[str]) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    for i, ln in enumerate(lines):
        for m in _RE_22DIG.finditer(ln):
            out.append((i, m.group(1)))
    return out

def _extract_cbu_cvu_quikipay(txt: str, expected_cbu: Optional[str] = None) -> Optional[str]:
    """
    Heurística específica QuikiPay para desambiguar CBU destino.
    """
    lines = _split_lines(txt)
    if not lines:
        return None

    # Índices de bloques
    benef_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"beneficiario", ln, flags=re.IGNORECASE)]
    origen_idxs = [i for i, ln in enumerate(lines) if re.fullmatch(r"origen", ln, flags=re.IGNORECASE)]

    # Todos los 22 dígitos con posición
    all_22 = _find_all_22_with_positions(lines)

    # 1) Si hay label 'CBU/CVU' dentro de Beneficiario, tomar primer 22 dígitos en 3–5 líneas
    if benef_idxs:
        for bidx in benef_idxs:
            # ventana de beneficiario
            block_end = min(len(lines), bidx + BENEF_WINDOW_DOWN + 1)
            block = lines[bidx:block_end]
            # buscar label dentro del bloque
            label_positions = [j for j, ln in enumerate(block) if re.fullmatch(r"cbu/cvu", ln, flags=re.IGNORECASE)]
            for j in label_positions:
                # mirar 5 líneas a partir del label (incluida la del label por si OCR mete todo junto)
                start = bidx + j
                end = min(len(lines), start + 6)
                near = lines[start:end]
                for ln in near:
                    m = _RE_22DIG.search(ln)
                    if m:
                        cand = m.group(1)
                        return cand  # prioridad máxima

    # 2) Si hay expected_cbu en cfg y aparece, usarlo
    if expected_cbu:
        exp = re.sub(r"\D", "", expected_cbu)
        if len(exp) == 22:
            for _, val in all_22:
                if val == exp:
                    return exp

    # 3) Quitar 22 dígitos que aparecen en ORIGEN
    origen_22: set[str] = set()
    for oidx in origen_idxs:
        o_end = min(len(lines), oidx + 12)  # ventana razonable para ORIGEN
        for i in range(oidx, o_end):
            for m in _RE_22DIG.finditer(lines[i]):
                origen_22.add(m.group(1))

    # 4) 22 dígitos en bloque Beneficiario (preferencia)
    benef_22: List[Tuple[int, str]] = []
    for bidx in benef_idxs or []:
        b_end = min(len(lines), bidx + BENEF_WINDOW_DOWN + 1)
        for i in range(bidx, b_end):
            for m in _RE_22DIG.finditer(lines[i]):
                val = m.group(1)
                if val not in origen_22:
                    benef_22.append((i, val))

    uniq_benef = sorted(set(v for _, v in benef_22))
    if len(uniq_benef) == 1:
        return uniq_benef[0]
    if len(uniq_benef) > 1:
        # 4.a) elegir el más cercano a un label CBU/CVU dentro de beneficiario
        best: Optional[Tuple[int, str, int]] = None  # (pos, val, distancia)
        for bidx in benef_idxs:
            b_end = min(len(lines), bidx + BENEF_WINDOW_DOWN + 1)
            # posiciones de label
            label_pos = [i for i in range(bidx, b_end) if re.fullmatch(r"cbu/cvu", lines[i], flags=re.IGNORECASE)]
            for pos, val in benef_22:
                if val not in uniq_benef:
                    continue
                # distancia a label más cercano
                if label_pos:
                    d = min(abs(pos - lp) for lp in label_pos)
                else:
                    d = 9999
                cand = (pos, val, d)
                if best is None or d < best[2] or (d == best[2] and pos > (best[0] if best else -1)):
                    best = cand
        if best:
            return best[1]
        # 4.b) si no hay labels, tomar el último del bloque beneficiario
        return sorted(benef_22, key=lambda x: x[0])[-1][1]

    # 5) Si no se pudo con Beneficiario, tomar el ÚLTIMO 22 dígitos del documento que no esté en ORIGEN
    non_origen_22 = [v for _, v in all_22 if v not in origen_22]
    if len(set(non_origen_22)) == 1:
        return non_origen_22[0]
    if non_origen_22:
        return non_origen_22[-1]

    # 6) Nada
    return None

# ───────────────────────────────────────────────────────────────────────────────
# API
# ───────────────────────────────────────────────────────────────────────────────

def extract(texto: str, *, cfg) -> dict:
    if not texto:
        raise ExtractionError("Texto vacío.")

    raw = texto
    txt = normalize_text_keep_lines(texto)

    monto = _extract_monto(txt)
    fecha_iso = _extract_fecha_iso(raw, txt)
    cbu = _extract_cbu_cvu_quikipay(txt, expected_cbu=cfg.get("cbu"))

    result = ParseResult(monto=monto, fecha=fecha_iso, cbu=cbu, alias=None)

    validate_all_expected(
        result,
        expected_amount=cfg["monto"],
        expected_date_iso=cfg["fecha"],
        expected_cbu=cfg.get("cbu"),
        expected_alias=cfg.get("alias"),
    )

    return dict(monto=result.monto, fecha=result.fecha, cbu=result.cbu, alias=result.alias)
