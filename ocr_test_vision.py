#!/usr/bin/env python3
import os, json, pathlib, re, time, uuid
from typing import List, Tuple
from google.cloud import vision
from google.protobuf.json_format import MessageToDict

# -------------------------------
# Configuración de paths
# -------------------------------
ROOT = pathlib.Path(__file__).resolve().parent
INPUT_DIR = ROOT / "backend" / "apps" / "pagos_core" / "management" / "commands" / "comprobantes"
OUT_DIR = ROOT / "ocr_outputs"
OUT_DIR.mkdir(exist_ok=True, parents=True)

# Bucket de GCS para PDFs (debe existir)
GCS_BUCKET = os.environ.get("VISION_OCR_BUCKET")
if not GCS_BUCKET:
    raise RuntimeError("⚠️  Debes definir la variable de entorno VISION_OCR_BUCKET")

# -------------------------------
# OCR para imágenes (JPEG, PNG)
# -------------------------------
def ocr_imagen(file_path: pathlib.Path) -> Tuple[str, dict]:
    """
    OCR para imágenes usando document_text_detection.
    Devuelve (texto, respuesta completa).
    """
    client = vision.ImageAnnotatorClient()
    with open(file_path, "rb") as f:
        image = vision.Image(content=f.read())
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(response.error.message)

    response_dict = MessageToDict(response._pb)
    full_text = response.full_text_annotation.text if response.full_text_annotation else ""

    return full_text, response_dict

# -------------------------------
# OCR para PDFs usando Vision Async + GCS
# -------------------------------
def ocr_pdf(file_path: pathlib.Path) -> Tuple[str, dict]:
    """
    OCR para PDFs usando async_batch_annotate_files con GCS.
    - Sube el archivo a GCS
    - Procesa OCR async
    - Descarga resultado como dict
    """
    from google.cloud import storage

    # 1. Subir archivo a bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    blob_id = f"ocr_uploads/{uuid.uuid4()}_{file_path.name}"
    blob = bucket.blob(blob_id)
    blob.upload_from_filename(str(file_path))

    # 2. Preparar URIs de entrada/salida
    gcs_source_uri = f"gs://{GCS_BUCKET}/{blob_id}"
    gcs_dest_prefix = f"ocr_results/{uuid.uuid4()}/"
    gcs_destination_uri = f"gs://{GCS_BUCKET}/{gcs_dest_prefix}"

    # 3. Crear cliente de Vision
    client = vision.ImageAnnotatorClient()
    mime_type = "application/pdf"

    # IMPORTANTE: usar objetos GcsSource y GcsDestination
    gcs_source = vision.GcsSource(uri=gcs_source_uri)
    gcs_destination = vision.GcsDestination(uri=gcs_destination_uri)

    input_config = vision.InputConfig(gcs_source=gcs_source, mime_type=mime_type)
    output_config = vision.OutputConfig(gcs_destination=gcs_destination, batch_size=1)

    async_request = vision.AsyncAnnotateFileRequest(
        features=[vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)],
        input_config=input_config,
        output_config=output_config,
    )

    operation = client.async_batch_annotate_files(requests=[async_request])
    print(f"  ⏳ Procesando PDF en Vision OCR... ({file_path.name})")
    operation.result(timeout=180)

    # 4. Descargar el JSON generado desde GCS
    result_blobs = list(storage_client.list_blobs(GCS_BUCKET, prefix=gcs_dest_prefix))
    if not result_blobs:
        raise RuntimeError("No se encontró salida OCR en GCS.")

    ocr_blob = result_blobs[0]
    ocr_json = json.loads(ocr_blob.download_as_text())

    response_dict = ocr_json["responses"][0]
    full_text = response_dict.get("fullTextAnnotation", {}).get("text", "")

    # 5. Limpiar blobs temporales
    blob.delete()
    ocr_blob.delete()

    return full_text, response_dict

# -------------------------------
# Análisis de posible edición
# -------------------------------
def analizar_edicion(response_dict: dict) -> dict:
    """
    Verifica:
    - Confianza promedio
    - Palabras con confianza < 0.6
    - Símbolos o caracteres sospechosos
    """
    palabras_sospechosas = []
    total_confianza = 0
    total_palabras = 0

    for page in response_dict.get("fullTextAnnotation", {}).get("pages", []):
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                for word in paragraph.get("words", []):
                    texto = "".join([s.get("text", "") for s in word.get("symbols", [])])
                    conf = word.get("confidence", 1.0)
                    total_confianza += conf
                    total_palabras += 1

                    if conf < 0.6 or re.search(r"[^\w\s\.,\$%:-]", texto):
                        palabras_sospechosas.append({
                            "texto": texto,
                            "confianza": round(conf, 2)
                        })

    promedio_confianza = round(total_confianza / total_palabras, 3) if total_palabras else 1.0

    return {
        "promedio_confianza": promedio_confianza,
        "palabras_sospechosas": palabras_sospechosas,
        "flag_riesgo_alto": promedio_confianza < 0.7 or len(palabras_sospechosas) >= 5
    }

# -------------------------------
# Procesamiento principal
# -------------------------------
def procesar_comprobantes():
    """
    Recorre todos los comprobantes, corre OCR (imagen o PDF)
    y genera el análisis de posible edición. No guarda OCR.
    """
    resultados = []
    archivos = sorted(INPUT_DIR.glob("*"))

    for archivo in archivos:
        if archivo.suffix.lower() not in [".jpg", ".jpeg", ".png", ".pdf"]:
            continue

        print(f"\nProcesando: {archivo.name}")
        try:
            if archivo.suffix.lower() == ".pdf":
                texto, response_dict = ocr_pdf(archivo)
            else:
                texto, response_dict = ocr_imagen(archivo)

            analisis = analizar_edicion(response_dict)

            resultados.append({
                "archivo": archivo.name,
                "texto": texto[:500],  # preview
                "promedio_confianza": analisis["promedio_confianza"],
                "palabras_sospechosas": analisis["palabras_sospechosas"],
                "flag_riesgo_alto": analisis["flag_riesgo_alto"],
            })

        except Exception as e:
            print(f"[ERROR] {archivo.name}: {e}")
            resultados.append({
                "archivo": archivo.name,
                "error": str(e)
            })

    # Guardar resumen final
    resumen_path = OUT_DIR / "resumen_analisis.json"
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Análisis terminado. Resultados en: {resumen_path}")

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    procesar_comprobantes()
