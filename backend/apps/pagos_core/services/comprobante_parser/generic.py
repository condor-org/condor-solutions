"""
Extractor GENÉRICO (modo soft) para comprobantes.

Objetivo:
- Operar sin conocimiento del banco.
- Aceptar todos los formatos vistos en extractores específicos.
- Ser BLANDO ante ambigüedad: usa heurísticas de proximidad/ventanas y, si hay cfg esperado,
  prioriza lo esperado para desempatar.

Cubre:
- Monto: AR/US, con/sin símbolo, miles/decimales, línea "limpia" y ventanas por etiquetas típicas.
- Fecha: ISO con/sin hora, variantes DMY/YMD, meses en español (largos y abreviados), AM/PM, "hs",
         tokens sueltos (YYYY MM DD HH mm [ss]).
- Destino: CBU/CVU (22 dígitos) y Alias; prioriza bloque destinatario/beneficiario/cuenta destino
           + labels (CBU/CVU/CBU/Alias/Alias), descarta ORIGEN y elige por cercanía al label; si sigue
           la ambigüedad, último no-origen. Si cfg trae cbu/alias, se prefiere.

Validación:
- Usa validate_all_expected, que reportará mismatch si el heurístico no coincide.

Logs:
- Emite logger.debug con la regla aplicada y candidatos evaluados.

NOTA:
- Este extractor es “último recurso”. registry debe invocarlo si ningún banco matchea.
"""

from __future__ import annotations
import re
import logging
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Iterable

from .base import (
    ParseResult, ExtractionError,
    normalize_text_keep_lines, validate_all_expected
)

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────────────
# Parámetros/ventanas
# ───────────────────────────────────────────────────────────────────────────────

AMOUNT_WINDOW_DOWN = 6
AMOUNT_WINDOW_UP   = 2
DEST_WINDOW_LINES  = 14
LABEL_NEAR_LINES   = 5
ORIGEN_WINDOW_DOWN = 12
FECHA_WINDOW_DOWN  = 5

AMOUNT_EPS = 0.01  # tolerancia centavos para matchear expected

# ───────────────────────────────────────────────────────────────────────────────
# Patrones unificados (montos, fechas, destino)
# ───────────────────────────────────────────────────────────────────────────────

# --- Montos ---
RE_MONEY_TOKEN = re.compile(
    r"(?i)(?:ar\$|us\$|\$|ars|usd)?\s*("
    r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?)"
    r"|"
    r"(?:\d+(?:[.,]\d{1,2})?)"
    r")"
)
RE_MONEY_LINE = re.compile(
    r"^\s*(?:ar\$|us\$|\$|ars|usd)?\s*("
    r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?)"
    r"|"
    r"(?:\d+(?:[.,]\d{1,2})?)"
    r")\s*$",
    re.IGNORECASE | re.MULTILINE
)
RE_INLINE_AMOUNT = re.compile(
    r"^\s*(importe|monto|monto\s+enviado|total)\s*:?\s*(?:ar\$|us\$|\$|ars|usd)?\s*([0-9][0-9.,]*)\s*$",
    re.IGNORECASE | re.MULTILINE
)

# Anchors/labels típicos de monto
RE_TIT_AMOUNT = [
    re.compile(r"^\s*importe\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*monto\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*monto\s+enviado\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*enviaste\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*total\s*$", re.IGNORECASE | re.MULTILINE),
]

# --- Fechas ---
# --- Fechas ---
# Separadores tolerantes: ASCII - / . y guiones Unicode (u2010–u2015)
SEP = r"[\/\-\.\u2010-\u2015]"
# 1) YYYY-MM-DD HH:MM[:SS]
RE_DT_ISO = re.compile(
    rf"\b(20\d{{2}}){SEP}(1[0-2]|0[1-9]){SEP}(3[01]|[12]\d|0[1-9])\s+(2[0-3]|[01]\d):([0-5]\d)(?::([0-5]\d))?\b"
)

# 2) ISO flexible (separadores varios, puede cruzar saltos)
RE_DT_ISO_FLEX = re.compile(
    rf"(20\d{{2}})\D+(1[0-2]|0[1-9])\D+(3[01]|[12]\d|0[1-9])(?:\D+(2[0-3]|[01]\d)\D+([0-5]\d)(?:\D+([0-5]\d))?)?",
    re.DOTALL
)

# 3) YYYY-MM-DD / YYYY/MM/DD
RE_DATE_YMD = re.compile(
    rf"\b(20\d{{2}}){SEP}(1[0-2]|0[1-9]){SEP}(3[01]|[12]\d|0[1-9])\b"
)

# 4) Tokens separados: YYYY MM DD [HH mm ss]
RE_DT_SPLIT = re.compile(
    r"\b(20\d{2})\s+(1[0-2]|0[1-9])\s+(3[01]|[12]\d|0[1-9])(?:\s+(2[0-3]|[01]\d)\s+([0-5]\d)(?:\s+([0-5]\d))?)?\b"
)
RE_DATE_DMY = re.compile(r"\b([0-3]?\d)[/\-]([0-1]?\d)[/\-](\d{4})\b")
RE_DATE_DMY_2DIG = re.compile(r"\b([0-3]?\d)[/\-]([0-1]?\d)[/\-](\d{2})\b")
RE_DATE_DMY_MON_ES = re.compile(r"\b([0-3]?\d)[/\-]([A-Za-z]{3,9})[/\-](\d{4})\b", re.IGNORECASE)
RE_DATE_LONG_ES = re.compile(
    r"\b(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo),?\s+"
    r"([0-3]?\d)\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})\b",
    re.IGNORECASE
)
RE_DATE_LONG_ES_NO_DOW = re.compile(
    r"\b([0-3]?\d)\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})\b",
    re.IGNORECASE
)

RE_TIME_24   = re.compile(r"\b(2[0-3]|[01]?\d):([0-5]\d)(?::([0-5]\d))?\s*(?:hs|h)?\b", re.IGNORECASE)
RE_TIME_AMPM = re.compile(r"\b(1[0-2]|0?\d):([0-5]\d)(?::([0-5]\d))?\s*(AM|PM)\b", re.IGNORECASE)

# Anchors de fecha
RE_TIT_FECHA = [
    re.compile(r"^\s*fecha\s+y\s+hora\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*fecha\s+de\s+operaci[oó]n\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*fecha\s*$", re.IGNORECASE | re.MULTILINE),
]

# Meses
MONTHS_ES: Dict[str, int] = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
    "noviembre":11,"diciembre":12,
    "ene":1,"feb":2,"mar":3,"abr":4,"may":5,"jun":6,"jul":7,"ago":8,"sep":9,"set":9,"oct":10,"nov":11,"dic":12,
}

# --- CBU/CVU/Alias ---
RE_22DIG = re.compile(r"\b(\d{22})\b")
RE_ALIAS = re.compile(r"\b([A-Za-z0-9](?:[A-Za-z0-9.\-]{4,23})[A-Za-z0-9])\b")

RE_TIT_DESTS = [
    re.compile(r"^\s*destinatario\s*$",     re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*para\s*$",             re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*beneficiario\s*$",     re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*cuenta\s+destino\s*$", re.IGNORECASE | re.MULTILINE),
]
RE_LABELS_DEST = [
    re.compile(r"^\s*cbu/cvu\s*:?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*cbu\s*:?\s*$",     re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*cvu\s*:?\s*$",     re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*cbu/alias\s*:?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*alias\s*:?\s*$",   re.IGNORECASE | re.MULTILINE),
]
RE_TIT_ORIGEN = re.compile(r"^\s*origen\s*$", re.IGNORECASE | re.MULTILINE)

# ───────────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────────

def _split_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln != ""]

def _is_plain_big_integer(token: str, *, min_len: int = 7) -> bool:
    s = token.strip()
    if "." in s or "," in s:
        return False
    return s.isdigit() and len(s) >= min_len

def _to_float_money(token: str) -> float:
    s = token.strip()
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")
    if last_comma > last_dot:
        return float(s.replace(".", "").replace(",", "."))
    if last_dot > -1 and (len(s) - last_dot - 1) == 2:
        return float(s.replace(",", ""))
    return float(s.replace(".", "").replace(",", ""))

def _iso_from_dmy(d: str, m: str, y: str) -> str:
    dt = date(year=int(y), month=int(m), day=int(d))
    return dt.isoformat()

def _iso_from_ymd(y: str, m: str, d: str) -> str:
    dt = date(year=int(y), month=int(m), day=int(d))
    return dt.isoformat()

def _iso_from_long_es(d: str, mes: str, y: str) -> str:
    norm = (mes.lower()
            .replace("á","a").replace("é","e").replace("í","i")
            .replace("ó","o").replace("ú","u"))
    mm = MONTHS_ES.get(norm)
    if not mm:
        raise ValueError(f"Mes no reconocido: {mes}")
    dt = date(year=int(y), month=int(mm), day=int(d))
    return dt.isoformat()

def _iso_from_dmy_mon_es(d: str, mon: str, y: str) -> str:
    mm = MONTHS_ES.get(mon.lower())
    if not mm:
        # fallback por si viene con acentos o mezclas
        return _iso_from_long_es(d, mon, y)
    dt = date(year=int(y), month=int(mm), day=int(d))
    return dt.isoformat()

def _iso_from_dmy_2dig(d: str, m: str, yy: str) -> str:
    y2 = int(yy)
    year = 2000 + y2 if y2 <= 79 else 1900 + y2
    dt = date(year=year, month=int(m), day=int(d))
    return dt.isoformat()

def _window_from_titles(lines: List[str], titles: Iterable[re.Pattern], down: int, up: int = 0) -> List[str]:
    idxs: List[int] = []
    for tit in titles:
        idxs.extend([i for i, ln in enumerate(lines) if tit.fullmatch(ln)])
    blocks: List[str] = []
    for idx in idxs:
        start = max(0, idx - up)
        end = min(len(lines), idx + down + 1)
        blocks.append("\n".join(lines[start:end]))
    return blocks


_UNICODE_DASHES = dict((ord(ch), '-') for ch in "\u2010\u2011\u2012\u2013\u2014\u2015")
_UNICODE_SPACES = dict((ord(ch), ' ') for ch in "\u00A0\u2007\u2009\u202F")
_BIDI_MARKS     = dict((ord(ch), None) for ch in "\u200B\u200C\u200D\u2060\u200E\u200F")

def _norm_date_separators(s: str) -> str:
    # Reemplaza guiones Unicode por '-', NBSP/thin spaces por ' ', y remueve marcas bidi/ZWSP
    return (s.translate(_UNICODE_DASHES)
             .translate(_UNICODE_SPACES)
             .translate(_BIDI_MARKS))
# ───────────────────────────────────────────────────────────────────────────────
# Extracción: MONTO (soft)
# ───────────────────────────────────────────────────────────────────────────────

def _extract_amount_soft(txt: str, expected: Optional[float]) -> float:
    lines = _split_lines(txt)

    # 0) Ventanas por títulos típicos
    candidate_vals: List[float] = []
    for block in _window_from_titles(lines, RE_TIT_AMOUNT, AMOUNT_WINDOW_DOWN, AMOUNT_WINDOW_UP):
        # preferí tokens con símbolo o con separadores
        tokens = []
        for m in RE_MONEY_TOKEN.finditer(block):
            t = m.group(1)
            if _is_plain_big_integer(t):
                continue
            if "." in t or "," in t:
                tokens.append(t)
        if tokens:
            vals = sorted({_to_float_money(t) for t in tokens})
            candidate_vals.extend(vals)

    if candidate_vals:
        uniq = sorted(set(candidate_vals))
        # 0.a) si hay expected y matchea por epsilon, devolvémoslo
        if expected is not None:
            for v in uniq:
                if abs(v - float(expected)) <= AMOUNT_EPS:
                    logger.debug("[generic] amount: window+expected hit → %s", v)
                    return v
        # 0.b) si hay más de uno, elegimos el MAYOR (monto total suele ser el mayor)
        chosen = max(uniq)
        logger.debug("[generic] amount: window heuristic → %s (cands=%s)", chosen, uniq)
        return chosen

    # 0.bis) Línea con label inline ("Monto: 123", "Importe: $ 1.234,56")
    inline_vals = []
    for m in RE_INLINE_AMOUNT.finditer(txt):
        t = m.group(2)
        if not _is_plain_big_integer(t):  # evita IDs como 950797
            inline_vals.append(_to_float_money(t))
    if inline_vals:
        uniq = sorted(set(inline_vals))
        if expected is not None:
            for v in uniq:
                if abs(v - float(expected)) <= AMOUNT_EPS:
                    logger.debug("[generic] amount: inline+expected → %s", v)
                    return v
        chosen = max(uniq)
        logger.debug("[generic] amount: inline pick → %s (cands=%s)", chosen, uniq)
        return chosen


    # 1) Línea “limpia”
    line_matches = [t for t in RE_MONEY_LINE.findall(txt) if not _is_plain_big_integer(t, min_len=6)]

    if line_matches:
        vals = sorted({_to_float_money(t) for t in line_matches})
        if expected is not None:
            for v in vals:
                if abs(v - float(expected)) <= AMOUNT_EPS:
                    logger.debug("[generic] amount: clean-line+expected → %s", v)
                    return v
        if len(vals) == 1:
            v = vals[0]
            logger.debug("[generic] amount: clean-line unique → %s", v)
            return v
        chosen = max(vals)
        logger.debug("[generic] amount: clean-line pick max → %s (vals=%s)", chosen, vals)
        return chosen

    # 2) Tokens globales
    tokens = [t for t in RE_MONEY_TOKEN.findall(txt) if not _is_plain_big_integer(t)]
    if not tokens:
        raise ExtractionError("No se encontró un monto reconocible.")
    vals = sorted({_to_float_money(t) for t in tokens})
    if expected is not None:
        for v in vals:
            if abs(v - float(expected)) <= AMOUNT_EPS:
                logger.debug("[generic] amount: global+expected → %s", v)
                return v
    if len(vals) == 1:
        v = vals[0]
        logger.debug("[generic] amount: global unique → %s", v)
        return v
    chosen = max(vals)
    logger.debug("[generic] amount: global pick max → %s (vals=%s)", chosen, vals)
    return chosen

# ───────────────────────────────────────────────────────────────────────────────
# Extracción: FECHA (soft)
# ───────────────────────────────────────────────────────────────────────────────

def _extract_date_soft(txt: str, expected_iso: Optional[str]) -> str:
    txt_n = _norm_date_separators(txt)
    lines = _split_lines(txt_n)

    def _collect_dates(source: str) -> List[Tuple[int, str]]:
        out: List[Tuple[int, str]] = []
        src_lines = _split_lines(source)
        for i, ln in enumerate(src_lines):
            # ISO con hora (fuerte)
            for m in RE_DT_ISO.finditer(ln):
                out.append((i, _iso_from_ymd(m.group(1), m.group(2), m.group(3))))
            # YMD puro
            for m in RE_DATE_YMD.finditer(ln):
                out.append((i, _iso_from_ymd(m.group(1), m.group(2), m.group(3))))
            # DMY 4
            for m in RE_DATE_DMY.finditer(ln):
                out.append((i, _iso_from_dmy(m.group(1), m.group(2), m.group(3))))
            # DMY 2
            for m in RE_DATE_DMY_2DIG.finditer(ln):
                out.append((i, _iso_from_dmy_2dig(m.group(1), m.group(2), m.group(3))))
            # D/MON/YYYY
            for m in RE_DATE_DMY_MON_ES.finditer(ln):
                out.append((i, _iso_from_dmy_mon_es(m.group(1), m.group(2), m.group(3))))
            # Largo ES
            for m in RE_DATE_LONG_ES.finditer(ln):
                out.append((i, _iso_from_long_es(m.group(1), m.group(2), m.group(3))))
            for m in RE_DATE_LONG_ES_NO_DOW.finditer(ln):
                out.append((i, _iso_from_long_es(m.group(1), m.group(2), m.group(3))))
        # ISO flex (puede cruzar saltos de línea u otros separadores)
        for m in RE_DT_ISO_FLEX.finditer(source):
            y, mo, d = m.group(1), m.group(2), m.group(3)
            out.append((0, _iso_from_ymd(y, mo, d)))
        # Split tokens (YYYY MM DD [HH mm ss])
        for m in RE_DT_SPLIT.finditer(source):
            y, mo, d = m.group(1), m.group(2), m.group(3)
            out.append((0, _iso_from_ymd(y, mo, d)))
        return out

    # 0) Ventanas de fecha (si existen títulos)
    candidate_dates: List[str] = []
    for block in _window_from_titles(lines, RE_TIT_FECHA, FECHA_WINDOW_DOWN):
        # 1) ISO exacto con hora (YYYY-MM-DD HH:MM[:SS]) dentro del bloque → prioridad máxima
        blk_dates = [ _iso_from_ymd(m.group(1), m.group(2), m.group(3)) for m in RE_DT_ISO.finditer(block) ]
        if not blk_dates:
            blk_dates = [ iso for _, iso in _collect_dates(block) ]
        candidate_dates.extend(blk_dates)

    if candidate_dates:
        uniq = sorted(set(candidate_dates))
        if expected_iso and expected_iso in uniq:
            logger.debug("[generic] date: window+expected → %s", expected_iso)
            return expected_iso
        if len(uniq) == 1:
            v = uniq[0]
            logger.debug("[generic] date: window unique → %s", v)
            return v
        # si varias: priorizar la que aparezca con hora cerca dentro del bloque
        for block in _window_from_titles(lines, RE_TIT_FECHA, FECHA_WINDOW_DOWN):
            blk_lines = _split_lines(block)
            for i, ln in enumerate(blk_lines):
                # si hay una fecha en esta línea y hora cerca, devolver esa
                d_candidates = []
                for m in RE_DT_ISO.finditer(ln):
                    d_candidates.append(_iso_from_ymd(m.group(1), m.group(2), m.group(3)))
                for m in RE_DATE_YMD.finditer(ln):
                    d_candidates.append(_iso_from_ymd(m.group(1), m.group(2), m.group(3)))
                for m in RE_DATE_DMY.finditer(ln):
                    d_candidates.append(_iso_from_dmy(m.group(1), m.group(2), m.group(3)))
                for m in RE_DATE_DMY_2DIG.finditer(ln):
                    d_candidates.append(_iso_from_dmy_2dig(m.group(1), m.group(2), m.group(3)))
                for m in RE_DATE_DMY_MON_ES.finditer(ln):
                    d_candidates.append(_iso_from_dmy_mon_es(m.group(1), m.group(2), m.group(3)))
                if d_candidates:
                    # hora en la misma línea o siguiente
                    if RE_TIME_24.search(ln) or RE_TIME_AMPM.search(ln) or (i + 1 < len(blk_lines) and (RE_TIME_24.search(blk_lines[i+1]) or RE_TIME_AMPM.search(blk_lines[i+1]))):
                        logger.debug("[generic] date: window near-time → %s", d_candidates[0])
                        return d_candidates[0]
        # sino, elegimos determinísticamente la primera en orden de aparición
        logger.debug("[generic] date: window pick first → %s (uniq=%s)", uniq[0], uniq)
        return uniq[0]

    # 1) Global (sin ventana)
    dated = _collect_dates(txt_n)
    if not dated:
        # último intento: buscar explícito ISO con hora (estricto y laxo)
        iso_inline = [ _iso_from_ymd(m.group(1), m.group(2), m.group(3)) for m in RE_DT_ISO.finditer(txt_n) ]
        if not iso_inline:
            iso_inline = [ _iso_from_ymd(m.group(1), m.group(2), m.group(3)) for m in RE_DT_ISO_FLEX.finditer(txt_n) ]
        if iso_inline:
            uniq_iso = sorted(set(iso_inline))
            logger.debug("[generic] date: ISO-with-time fallback → %s (cands=%s)", uniq_iso[0], uniq_iso)
            return uniq_iso[0]
        raise ExtractionError("No se encontró una fecha válida.")
    uniq_all = sorted(set(iso for _, iso in dated))
    if expected_iso and expected_iso in uniq_all:
        logger.debug("[generic] date: global+expected → %s", expected_iso)
        return expected_iso
    if len(uniq_all) == 1:
        v = uniq_all[0]
        logger.debug("[generic] date: global unique → %s", v)
        return v

    # prioridad a fechas con hora cercana (misma línea o siguiente)
    lines = _split_lines(txt_n)
    with_time: List[str] = []
    for i, ln in enumerate(lines):
        found_here = []
        for m in RE_DT_ISO.finditer(ln):
            found_here.append(_iso_from_ymd(m.group(1), m.group(2), m.group(3)))
        for m in RE_DATE_YMD.finditer(ln):
            found_here.append(_iso_from_ymd(m.group(1), m.group(2), m.group(3)))
        for m in RE_DATE_DMY.finditer(ln):
            found_here.append(_iso_from_dmy(m.group(1), m.group(2), m.group(3)))
        for m in RE_DATE_DMY_2DIG.finditer(ln):
            found_here.append(_iso_from_dmy_2dig(m.group(1), m.group(2), m.group(3)))
        for m in RE_DATE_DMY_MON_ES.finditer(ln):
            found_here.append(_iso_from_dmy_mon_es(m.group(1), m.group(2), m.group(3)))
        if found_here:
            if RE_TIME_24.search(ln) or RE_TIME_AMPM.search(ln) or (i + 1 < len(lines) and (RE_TIME_24.search(lines[i+1]) or RE_TIME_AMPM.search(lines[i+1]))):
                with_time.extend(found_here)
    with_time = sorted(set(with_time))
    if expected_iso and expected_iso in with_time:
        logger.debug("[generic] date: global near-time+expected → %s", expected_iso)
        return expected_iso
    if len(with_time) == 1:
        logger.debug("[generic] date: global near-time unique → %s", with_time[0])
        return with_time[0]
    # blando: elegimos la primera en orden de aparición
    logger.debug("[generic] date: global pick first → %s (uniq=%s)", uniq_all[0], uniq_all)
    return uniq_all[0]

# ───────────────────────────────────────────────────────────────────────────────
# Extracción: DESTINO (soft)
# ───────────────────────────────────────────────────────────────────────────────

def _find_all_22_with_positions(lines: List[str]) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    for i, ln in enumerate(lines):
        for m in RE_22DIG.finditer(ln):
            out.append((i, m.group(1)))
    return out

def _extract_destination_soft(txt: str, expected_cbu: Optional[str], expected_alias: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    lines = _split_lines(txt)
    if not lines:
        return (None, None)

    # 0) expected preferencia
    exp_cbu = re.sub(r"\D", "", expected_cbu) if expected_cbu else None
    if exp_cbu and len(exp_cbu) != 22:
        exp_cbu = None
    exp_alias = expected_alias.strip() if isinstance(expected_alias, str) else None

    # 1) Ventanas por títulos destino
    cands_cbu: List[Tuple[int, str]] = []
    cands_alias: List[Tuple[int, str]] = []
    label_positions: List[int] = []

    for tit in RE_TIT_DESTS:
        dest_idxs = [i for i, ln in enumerate(lines) if tit.fullmatch(ln)]
        for idx in dest_idxs:
            start = idx
            end = min(len(lines), idx + DEST_WINDOW_LINES + 1)
            block = lines[start:end]

            # labels en bloque
            lbl_pos = []
            for lab in RE_LABELS_DEST:
                lbl_pos.extend([j for j, ln in enumerate(block) if lab.fullmatch(ln)])
            label_positions.extend([start + j for j in lbl_pos])

            # candidatos cerca de labels
            for j in lbl_pos:
                seg = "\n".join(block[j : min(len(block), j + LABEL_NEAR_LINES + 1)])
                for m in RE_22DIG.finditer(seg):
                    cands_cbu.append((start + j, m.group(1)))
                for m in RE_ALIAS.finditer(seg):
                    if not m.group(1).isdigit():
                        cands_alias.append((start + j, m.group(1)))

            # candidatos en todo el bloque
            blk_text = "\n".join(block)
            for m in RE_22DIG.finditer(blk_text):
                cands_cbu.append((start, m.group(1)))
            for m in RE_ALIAS.finditer(blk_text):
                if not m.group(1).isdigit():
                    cands_alias.append((start, m.group(1)))

    # 2) Excluir CBU que aparezcan bajo ORIGEN
    origen_idxs = [i for i, ln in enumerate(lines) if RE_TIT_ORIGEN.fullmatch(ln)]
    origen_22: set[str] = set()
    for oidx in origen_idxs:
        o_end = min(len(lines), oidx + ORIGEN_WINDOW_DOWN)
        for i in range(oidx, o_end):
            for m in RE_22DIG.finditer(lines[i]):
                origen_22.add(m.group(1))
    cands_cbu = [(pos, v) for (pos, v) in cands_cbu if v not in origen_22]

    # 3) Resolver por expected
    if exp_cbu:
        all22 = _find_all_22_with_positions(lines)   # [(pos, '22dig'), ...]
        non_origen_vals = {v for _, v in all22 if v not in origen_22}
        if exp_cbu in non_origen_vals:
            logger.debug("[generic] dest: short-circuit expected CBU → %s", exp_cbu)
            return (exp_cbu, None)
    if exp_alias:
        for _, a in cands_alias:
            if a.lower() == exp_alias.lower():
                logger.debug("[generic] dest: expected alias matched in window → %s", a)
                return (None, a)

    # 4) Cercanía a label CBU/CVU en bloque destino
    if cands_cbu:
        if label_positions:
            best = None  # (dist, pos, val)
            for pos, val in cands_cbu:
                dist = min(abs(pos - lp) for lp in label_positions) if label_positions else 9999
                tup = (dist, pos, val)
                if best is None or tup < best:
                    best = tup
            chosen = best[2]  # type: ignore
            logger.debug("[generic] dest: CBU nearest-to-label → %s (dist=%s)", chosen, best[0] if best else None)
            return (chosen, None)
        # si no hay labels, tomamos el último CBU visto en ventanas de destino
        chosen = sorted(cands_cbu, key=lambda x: x[0])[-1][1]
        logger.debug("[generic] dest: CBU last-in-dest-window → %s", chosen)
        return (chosen, None)

    if cands_alias:
        # único alias en ventanas de destino
        uniq_alias = sorted(set(a for _, a in cands_alias))
        if exp_alias and exp_alias in uniq_alias:
            logger.debug("[generic] dest: alias expected in dest-window → %s", exp_alias)
            return (None, exp_alias)
        if len(uniq_alias) == 1:
            logger.debug("[generic] dest: single alias in dest-window → %s", uniq_alias[0])
            return (None, uniq_alias[0])
        # si varios, elegir el último visto
        chosen_a = sorted(cands_alias, key=lambda x: x[0])[-1][1]
        logger.debug("[generic] dest: alias last-in-dest-window → %s", chosen_a)
        return (None, chosen_a)

    # 5) Fallback global
    # 5.a) Alias: "Alias: foo.bar"
    alias_global = [m.group(1) for m in re.finditer(r"alias:\s*([A-Za-z0-9][A-Za-z0-9.\-]{4,23}[A-Za-z0-9])", txt, flags=re.IGNORECASE)]
    alias_global = [a for a in alias_global if not a.isdigit()]
    if exp_alias and any(a.lower() == exp_alias.lower() for a in alias_global):
        logger.debug("[generic] dest: alias expected found global → %s", exp_alias)
        return (None, exp_alias)
    if len(set(alias_global)) == 1:
        logger.debug("[generic] dest: single alias global → %s", alias_global[0])
        return (None, alias_global[0])

    # 5.b) CBU global: preferir último no-origen
    all_22 = _find_all_22_with_positions(lines)
    non_origen = [v for (pos, v) in all_22 if v not in origen_22]
    if exp_cbu and any(v == exp_cbu for v in non_origen):
        logger.debug("[generic] dest: expected CBU found global → %s", exp_cbu)
        return (exp_cbu, None)
    if len(set(non_origen)) == 1:
        logger.debug("[generic] dest: single CBU non-origen global → %s", non_origen[0])
        return (non_origen[0], None)
    if non_origen:
        chosen = non_origen[-1]
        logger.debug("[generic] dest: CBU pick last non-origen global → %s", chosen)
        return (chosen, None)

    # Nada seguro
    logger.debug("[generic] dest: no CBU/Alias resolved")
    return (None, None)

# ───────────────────────────────────────────────────────────────────────────────
# API
# ───────────────────────────────────────────────────────────────────────────────

def matches(texto: str) -> bool:
    """El genérico está disponible como fallback (no hace falta ‘match’ real)."""
    return True

def extract(texto: str, *, cfg) -> dict:
    """
    Extrae {monto, fecha, cbu, alias} de manera BLANDA y valida con cfg.
    Usa ‘normalize_text_keep_lines’; si tu normalización altera '- : /', conviene preservarlos.
    """
    if not texto:
        raise ExtractionError("Texto vacío.")

    txt = normalize_text_keep_lines(texto)

    expected_amount = float(cfg["monto"]) if "monto" in cfg and cfg["monto"] is not None else None
    expected_date   = cfg.get("fecha")  # 'YYYY-MM-DD'
    expected_cbu    = cfg.get("cbu")
    expected_alias  = cfg.get("alias")

    monto = _extract_amount_soft(txt, expected_amount)
    fecha_iso = _extract_date_soft(txt, expected_date)
    cbu, alias = _extract_destination_soft(txt, expected_cbu, expected_alias)

    result = ParseResult(monto=monto, fecha=fecha_iso, cbu=cbu, alias=alias)

    # Validación de negocio (exact match con lo esperado)
    validate_all_expected(
        result,
        expected_amount=expected_amount,
        expected_date_iso=expected_date,
        expected_cbu=expected_cbu,
        expected_alias=expected_alias,
    )

    logger.debug("[generic] final result → monto=%.2f fecha=%s cbu=%s alias=%s", result.monto, result.fecha, result.cbu, result.alias)
    return dict(monto=result.monto, fecha=result.fecha, cbu=result.cbu, alias=result.alias)
