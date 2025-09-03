"""
Proveedor de OCR con Google Cloud Vision.

API pública:
- extract_text(file_input) -> dict:
    Acepta:
      * pathlib.Path / str (ruta a archivo)
      * file-like (objeto con .read()) para imágenes
    Detecta tipo por extensión: PDF -> async GCS; IMG -> document_text_detection.
    Devuelve:
      {
        "texto": str,
        "avg_confidence": float,
        "suspicious_tokens": list[{"texto": str, "confianza": float}],
        "engine": "gcv_document_text_detection|gcv_async_pdf",
        "raw_response": dict  # útil para debugging (no usar en validación)
      }

- is_trustable(meta) -> bool:
    Regla estricta:
      * promedio de confianza >= 0.7
      * hasta 5 palabras sospechosas
"""

from __future__ import annotations
import os
import io
import json
import re
import uuid
import pathlib
from typing import Any, Dict, Tuple, Union, List, IO, Optional

# Imports lazy dentro de helpers para permitir importar el módulo
# aunque no estén instaladas las libs (fallará recién al usarlas).
from google.oauth2 import service_account  # type: ignore


# ───────────────────────────────────────────────────────────────────────────────
# Credenciales desde variables de entorno (private key suelta)
# ───────────────────────────────────────────────────────────────────────────────

def _build_credentials():
    """
    Construye service_account.Credentials a partir de:
      - GCP_SA_CLIENT_EMAIL (obligatorio)
      - GCP_SA_PROJECT_ID (obligatorio)
      - GOOGLE_CREDS (private key completa, con \n escapados) (obligatorio)
    """
    client_email = os.environ.get("GCP_SA_CLIENT_EMAIL")
    project_id = os.environ.get("GCP_SA_PROJECT_ID")
    private_key = os.environ.get("GOOGLE_CREDS")

    if not client_email or not project_id or not private_key:
        missing = [k for k, v in {
            "GCP_SA_CLIENT_EMAIL": client_email,
            "GCP_SA_PROJECT_ID": project_id,
            "GOOGLE_CREDS": private_key,
        }.items() if not v]
        raise RuntimeError(f"Faltan variables de entorno para GCP: {', '.join(missing)}")

    # Normalizar saltos de línea escapados
    private_key = private_key.replace("\\n", "\n")

    info = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": "ignored",
        "private_key": private_key,
        "client_email": client_email,
        "client_id": "ignored",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
        "universe_domain": "googleapis.com",
    }
    scopes = [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/devstorage.read_write",
    ]
    creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
    return creds


def _vision_client():
    from google.cloud import vision  # type: ignore
    return vision.ImageAnnotatorClient(credentials=_build_credentials())


def _storage_client():
    from google.cloud import storage  # type: ignore
    return storage.Client(credentials=_build_credentials())


# ───────────────────────────────────────────────────────────────────────────────
# Helpers de tipo de archivo y lectura
# ───────────────────────────────────────────────────────────────────────────────

_PathLike = Union[str, pathlib.Path]
_FileLike = IO[bytes]
_Input = Union[_PathLike, _FileLike]

def _is_pdf_path(p: _PathLike) -> bool:
    return str(p).lower().endswith(".pdf")

def _is_image_path(p: _PathLike) -> bool:
    suf = str(p).lower()
    return suf.endswith(".jpg") or suf.endswith(".jpeg") or suf.endswith(".png") or suf.endswith(".webp")

def _read_all_bytes(f: _Input) -> bytes:
    if hasattr(f, "read"):
        return f.read()  # type: ignore[no-any-return]
    # f es ruta
    with open(str(f), "rb") as fh:
        return fh.read()


# ───────────────────────────────────────────────────────────────────────────────
# OCR Imagen (document_text_detection)
# ───────────────────────────────────────────────────────────────────────────────

def _ocr_image(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    from google.cloud import vision  # type: ignore
    from google.protobuf.json_format import MessageToDict  # type: ignore

    client = _vision_client()
    image = vision.Image(content=file_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(response.error.message)

    response_dict = MessageToDict(response._pb)
    full_text = response.full_text_annotation.text if response.full_text_annotation else ""
    return full_text or "", response_dict


# ───────────────────────────────────────────────────────────────────────────────
# OCR PDF (async_batch_annotate_files + GCS)
# ───────────────────────────────────────────────────────────────────────────────

def _ocr_pdf_via_gcs(pdf_path: _PathLike) -> Tuple[str, Dict[str, Any]]:
    """
    Pipeline:
      1) Subir PDF al bucket GCS (VISION_OCR_BUCKET)
      2) async_batch_annotate_files (DOCUMENT_TEXT_DETECTION)
      3) Descargar JSON de salida y devolver texto + dict
      4) Limpiar blobs temporales
    """
    from google.cloud import vision  # type: ignore
    import json as _json

    bucket_name = os.environ.get("VISION_OCR_BUCKET")
    if not bucket_name:
        raise RuntimeError("Debe definirse VISION_OCR_BUCKET para procesar PDFs con Vision.")

    storage_client = _storage_client()
    bucket = storage_client.bucket(bucket_name)

    blob_id = f"ocr_uploads/{uuid.uuid4()}_{pathlib.Path(str(pdf_path)).name}"
    blob = bucket.blob(blob_id)
    blob.upload_from_filename(str(pdf_path))

    # Configurar destinos
    gcs_source_uri = f"gs://{bucket_name}/{blob_id}"
    gcs_dest_prefix = f"ocr_results/{uuid.uuid4()}/"
    gcs_destination_uri = f"gs://{bucket_name}/{gcs_dest_prefix}"

    client = _vision_client()
    gcs_source = vision.GcsSource(uri=gcs_source_uri)
    gcs_destination = vision.GcsDestination(uri=gcs_destination_uri)
    input_config = vision.InputConfig(gcs_source=gcs_source, mime_type="application/pdf")
    output_config = vision.OutputConfig(gcs_destination=gcs_destination, batch_size=1)

    async_request = vision.AsyncAnnotateFileRequest(
        features=[vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)],
        input_config=input_config,
        output_config=output_config,
    )

    op = client.async_batch_annotate_files(requests=[async_request])
    op.result(timeout=180)

    # Descargar primer resultado
    result_blobs = list(storage_client.list_blobs(bucket_name, prefix=gcs_dest_prefix))
    if not result_blobs:
        # limpieza de subida
        try: blob.delete()
        except Exception: pass
        raise RuntimeError("No se encontró salida OCR en GCS.")

    ocr_blob = result_blobs[0]
    ocr_json = _json.loads(ocr_blob.download_as_text())

    response_dict = ocr_json["responses"][0]
    full_text = response_dict.get("fullTextAnnotation", {}).get("text", "") or ""

    # limpieza
    try: blob.delete()
    except Exception: pass
    try: ocr_blob.delete()
    except Exception: pass

    return full_text, response_dict


# ───────────────────────────────────────────────────────────────────────────────
# Análisis de confiabilidad a partir del response de Vision
# ───────────────────────────────────────────────────────────────────────────────

def _analyze_response(response_dict: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Devuelve:
      - promedio de confianza (palabra)
      - lista de 'palabras sospechosas' (conf < 0.6 o caracteres raros)
    """
    palabras_sospechosas: List[Dict[str, Any]] = []
    total_confianza = 0.0
    total_palabras = 0

    pages = response_dict.get("fullTextAnnotation", {}).get("pages", [])
    for page in pages:
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                for word in paragraph.get("words", []):
                    texto = "".join([s.get("text", "") for s in word.get("symbols", [])])
                    conf = float(word.get("confidence", 1.0))
                    total_confianza += conf
                    total_palabras += 1
                    if conf < 0.6 or re.search(r"[^\w\s\.,\$%:/\-]", texto):
                        palabras_sospechosas.append({
                            "texto": texto,
                            "confianza": round(conf, 2),
                        })

    avg = round(total_confianza / total_palabras, 4) if total_palabras else 1.0
    return avg, palabras_sospechosas


# ───────────────────────────────────────────────────────────────────────────────
# API principal
# ───────────────────────────────────────────────────────────────────────────────

def extract_text(file_input: _Input) -> Dict[str, Any]:
    """
    Ejecuta OCR con Google Vision.
    - Si file_input es Path/str:
        * .pdf → pipeline async GCS
        * imagen → document_text_detection con bytes
    - Si file_input es file-like:
        * asumimos imagen (JPEG/PNG/WEBP/PDF no soportado vía bytes aquí)

    Retorna dict con texto, métricas de confianza y engine.
    """
    # Caso ruta
    if isinstance(file_input, (str, pathlib.Path)):
        p = pathlib.Path(str(file_input))
        if _is_pdf_path(p):
            texto, resp = _ocr_pdf_via_gcs(p)
            avg, weird = _analyze_response(resp)
            return {
                "texto": texto,
                "avg_confidence": avg,
                "suspicious_tokens": weird,
                "engine": "gcv_async_pdf",
                "raw_response": resp,
            }
        elif _is_image_path(p):
            data = _read_all_bytes(p)
            texto, resp = _ocr_image(data)
            avg, weird = _analyze_response(resp)
            return {
                "texto": texto,
                "avg_confidence": avg,
                "suspicious_tokens": weird,
                "engine": "gcv_document_text_detection",
                "raw_response": resp,
            }
        else:
            # Intentar como imagen por bytes (p.ej. .jpeg/.jpg/.png no estándar)
            data = _read_all_bytes(p)
            texto, resp = _ocr_image(data)
            avg, weird = _analyze_response(resp)
            return {
                "texto": texto,
                "avg_confidence": avg,
                "suspicious_tokens": weird,
                "engine": "gcv_document_text_detection",
                "raw_response": resp,
            }

    # Caso file-like → tratamos como imagen
    if hasattr(file_input, "read"):
        data = file_input.read()  # type: ignore
        if not isinstance(data, (bytes, bytearray)):
            raise RuntimeError("file-like no devolvió bytes.")
        texto, resp = _ocr_image(data)
        avg, weird = _analyze_response(resp)
        return {
            "texto": texto,
            "avg_confidence": avg,
            "suspicious_tokens": weird,
            "engine": "gcv_document_text_detection",
            "raw_response": resp,
        }

    raise TypeError("file_input debe ser Path/str o file-like de bytes.")


def is_trustable(meta: Dict[str, Any]) -> bool:
    """
    Aplica tu política de confiabilidad:
      - avg_confidence >= 0.7
      - <= 5 palabras sospechosas
    """
    avg = float(meta.get("avg_confidence") or 0.0)
    weird = meta.get("suspicious_tokens") or []
    return (avg >= 0.7) and (len(weird) <= 5)
