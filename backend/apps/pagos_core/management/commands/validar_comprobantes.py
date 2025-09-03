from __future__ import annotations
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError

# Orquestación y OCR
from apps.pagos_core.services import ocr_providers
from apps.pagos_core.services.comprobante_parser import registry
from apps.pagos_core.services.comprobante_parser.base import ExtractionError

# YAML seguro (ruamel.yaml o PyYAML). Usamos PyYAML por simplicidad.
try:
    import yaml
except Exception as e:
    raise CommandError("PyYAML es requerido (pip install pyyaml)") from e


logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────────
# Constantes de paths
# ───────────────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
COMPROBANTES_DIR = ROOT / "comprobantes"
ESPERADOS_CANDIDATES = [
    COMPROBANTES_DIR / "esperados.yaml",
    COMPROBANTES_DIR / "esperados.yml",
]

OUT_DIR = ROOT.parent.parent.parent.parent / "tmp_reports"  # backend/tmp_reports
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ───────────────────────────────────────────────────────────────────────────────
# Utilidades de normalización para “esperados”
# ───────────────────────────────────────────────────────────────────────────────

_MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

_RE_DMY = re.compile(r"^([0-3]?\d)/([0-1]?\d)/(\d{2}|\d{4})$")
_RE_YMD = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_RE_LONG_ES = re.compile(r"^([0-3]?\d)\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})$")

def _iso_from_any_date(s: str) -> str:
    """
    Normaliza fechas esperadas a 'YYYY-MM-DD'.
    Soporta:
      - 'YYYY-MM-DD'
      - 'DD/MM/YY'  (→ 20YY) y 'DD/MM/YYYY'
      - 'DD de <mes> de YYYY' (en español)
    """
    if not s:
        raise ValueError("Fecha esperada vacía")

    s = s.strip()

    m = _RE_YMD.match(s)
    if m:
        y, mo, d = map(int, m.groups())
        return date(y, mo, d).isoformat()

    m = _RE_DMY.match(s)
    if m:
        d, mo, y = m.groups()
        d, mo = int(d), int(mo)
        if len(y) == 2:
            yy = int(y)
            y = 2000 + yy if yy <= 79 else 1900 + yy
        else:
            y = int(y)
        return date(y, mo, d).isoformat()

    m = _RE_LONG_ES.match(s.lower())
    if m:
        d, mes, y = m.groups()
        d, y = int(d), int(y)
        norm = (mes
                .lower()
                .replace("á", "a").replace("é", "e").replace("í", "i")
                .replace("ó", "o").replace("ú", "u"))
        mm = _MONTHS_ES.get(norm)
        if not mm:
            raise ValueError(f"Mes no reconocido en fecha esperada: {mes}")
        return date(y, mm, d).isoformat()

    raise ValueError(f"Formato de fecha esperada no soportado: {s}")


def _float_from_amount(x: Any) -> float:
    """
    Convierte el 'monto' esperado a float.
    Acepta:
      - número (int/float)
      - string con separadores: '1.234,56', '1,234.56', '1234,56', '1234.56'
    """
    if isinstance(x, (int, float)):
        return float(x)
    if not isinstance(x, str):
        raise ValueError(f"Tipo de monto no soportado: {type(x)}")

    s = x.strip()
    last_comma, last_dot = s.rfind(","), s.rfind(".")
    if last_comma > last_dot:
        # formato AR: ',' decimal
        return float(s.replace(".", "").replace(",", "."))
    # formato US o entero
    return float(s.replace(",", ""))


def _normalize_expected(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapta las claves del YAML a la config que consumen los extractores:
      - monto: float
      - fecha: 'YYYY-MM-DD'
      - cbu / alias: opcionales
    Además tolera variantes como:
      - alias_destino / cbu_destino
      - CVU en lugar de CBU (mismo formato de 22 dígitos)
    """
    exp = entry.get("esperado", {}) or {}

    cfg: Dict[str, Any] = {}

    # monto
    if "monto" not in exp:
        raise ValueError("Falta 'monto' en esperado")
    cfg["monto"] = _float_from_amount(exp["monto"])

    # fecha
    if "fecha" not in exp:
        raise ValueError("Falta 'fecha' en esperado")
    cfg["fecha"] = _iso_from_any_date(str(exp["fecha"]))

    # destino (cbu/alias) en varias keys posibles
    cbu = exp.get("cbu") or exp.get("cbu_destino") or exp.get("cvu") or exp.get("cvu_destino")
    alias = exp.get("alias") or exp.get("alias_destino")

    # normalizar strings (quitar espacios)
    if isinstance(cbu, str):
        cbu = re.sub(r"\D", "", cbu)
    if isinstance(alias, str):
        alias = alias.strip()

    if cbu:
        cfg["cbu"] = cbu
    if alias:
        cfg["alias"] = alias

    return cfg


# ───────────────────────────────────────────────────────────────────────────────
# Ejecutor por comprobante
# ───────────────────────────────────────────────────────────────────────────────

@dataclass
class CaseResult:
    archivo: str
    banco_yaml: Optional[str]
    banco_detectado: Optional[str]
    ocr_engine: Optional[str]
    ocr_avg_conf: Optional[float]
    ocr_suspicious_count: Optional[int]
    trustable: bool
    passed: bool
    error: Optional[str]
    parsed: Optional[Dict[str, Any]]

def _detect_extractor_name(module) -> str:
    """
    Devuelve un nombre legible del extractor (módulo) para el reporte.
    Por ejemplo: 'bbva', 'macro', 'galicia', o 'generic'.
    """
    try:
        name = getattr(module, "__name__", "")
        return name.split(".")[-1] or "unknown"
    except Exception:
        return "unknown"


def _run_single_case(case_entry: Dict[str, Any]) -> CaseResult:
    """
    Procesa un caso del YAML:
      - Corre OCR y verifica confiabilidad (is_trustable)
      - Selecciona extractor por texto OCR
      - Construye cfg desde 'esperado'
      - Ejecuta extractor y compara (validación interna)
    Devuelve un CaseResult con PASS/FAIL y detalles.
    """
    archivo = case_entry.get("archivo")
    banco_yaml = case_entry.get("banco")

    if not archivo:
        raise CommandError("Entrada YAML sin 'archivo'.")

    file_path = COMPROBANTES_DIR / archivo
    if not file_path.exists():
        raise CommandError(f"Archivo no encontrado: {file_path}")

    # 1) OCR
    ocr_meta = ocr_providers.extract_text(file_path)
    texto = ocr_meta.get("texto", "") or ""
    ocr_engine = ocr_meta.get("engine")
    ocr_avg_conf = ocr_meta.get("avg_confidence")
    suspicious = ocr_meta.get("suspicious_tokens") or []
    trustable = bool(ocr_providers.is_trustable(ocr_meta))

    if not trustable:
        # OCR no confiable → se rechaza el comprobante directamente
        return CaseResult(
            archivo=archivo,
            banco_yaml=banco_yaml,
            banco_detectado=None,
            ocr_engine=ocr_engine,
            ocr_avg_conf=ocr_avg_conf,
            ocr_suspicious_count=len(suspicious),
            trustable=False,
            passed=False,
            error="OCR no confiable (avg_conf < 0.7 o demasiados tokens sospechosos).",
            parsed=None,
        )

    # 2) Elegir extractor por texto OCR
    extractor = registry.find_extractor(texto) or None
    if extractor is None:
        # Si tu registry NO incluye 'generic' al final, podrías usarlo explícitamente acá.
        from apps.pagos_core.services.comprobante_parser import generic as extractor_generic
        extractor = extractor_generic
    banco_detectado = _detect_extractor_name(extractor)

    # 3) Armar cfg desde “esperado”
    cfg = _normalize_expected(case_entry)

    # 4) Ejecutar extractor + validación (los extractores ya validan contra cfg)
    try:
        parsed = extractor.extract(texto, cfg=cfg)
        # Si no lanzó excepción, se considera válido
        return CaseResult(
            archivo=archivo,
            banco_yaml=banco_yaml,
            banco_detectado=banco_detectado,
            ocr_engine=ocr_engine,
            ocr_avg_conf=ocr_avg_conf,
            ocr_suspicious_count=len(suspicious),
            trustable=True,
            passed=True,
            error=None,
            parsed=parsed,
        )
    except ExtractionError as e:
        return CaseResult(
            archivo=archivo,
            banco_yaml=banco_yaml,
            banco_detectado=banco_detectado,
            ocr_engine=ocr_engine,
            ocr_avg_conf=ocr_avg_conf,
            ocr_suspicious_count=len(suspicious),
            trustable=True,
            passed=False,
            error=f"ExtractionError: {e}",
            parsed=None,
        )
    except Exception as e:
        return CaseResult(
            archivo=archivo,
            banco_yaml=banco_yaml,
            banco_detectado=banco_detectado,
            ocr_engine=ocr_engine,
            ocr_avg_conf=ocr_avg_conf,
            ocr_suspicious_count=len(suspicious),
            trustable=True,
            passed=False,
            error=f"Unhandled error: {e}",
            parsed=None,
        )


# ───────────────────────────────────────────────────────────────────────────────
# Command
# ───────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Valida comprobantes reales contra 'esperados.yml' usando Vision OCR + extractores estrictos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default=str(OUT_DIR / "validaciones_resultados.json"),
            help="Ruta de salida para el JSON de resultados.",
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Detenerse en el primer FAIL.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Verboso de consola (INFO).",
        )

    def handle(self, *args, **options):
        if options.get("verbose"):
            logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        else:
            logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

        # 1) Cargar YAML
        esperados_path = None
        for cand in ESPERADOS_CANDIDATES:
            if cand.exists():
                esperados_path = cand
                break
        if not esperados_path:
            raise CommandError(f"No se encontró esperados.yaml/yml en {COMPROBANTES_DIR}")

        with open(esperados_path, "r", encoding="utf-8") as fh:
            entries = yaml.safe_load(fh) or []
        if not isinstance(entries, list) or not entries:
            raise CommandError("El archivo esperados.yml(a) no contiene una lista de casos.")

        # 2) Ejecutar casos
        results: List[CaseResult] = []
        passed = failed = 0

        for entry in entries:
            try:
                res = _run_single_case(entry)
                results.append(res)
                if res.passed:
                    passed += 1
                    self.stdout.write(self.style.SUCCESS(f"[PASS] {res.archivo}  (detected={res.banco_detectado}, conf={res.ocr_avg_conf})"))
                else:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f"[FAIL] {res.archivo}  (detected={res.banco_detectado})  -> {res.error}"))
                    if options.get("fail_fast"):
                        break
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"[ERROR] {entry.get('archivo','<sin-archivo>')}: {e}"))
                if options.get("fail_fast"):
                    break

        # 3) Guardar JSON completo
        out_path = Path(options["out"]).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = [
            {
                "archivo": r.archivo,
                "banco_yaml": r.banco_yaml,
                "banco_detectado": r.banco_detectado,
                "ocr_engine": r.ocr_engine,
                "ocr_avg_conf": r.ocr_avg_conf,
                "ocr_suspicious_count": r.ocr_suspicious_count,
                "trustable": r.trustable,
                "passed": r.passed,
                "error": r.error,
                "parsed": r.parsed,
            }
            for r in results
        ]
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(serializable, fh, indent=2, ensure_ascii=False)

        # 4) Resumen
        total = len(results)
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(f"Total: {total} | PASS: {passed} | FAIL: {failed}"))
        self.stdout.write(f"Reporte JSON → {out_path}")
