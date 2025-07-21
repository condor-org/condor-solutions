import os
from pathlib import Path
from PyPDF2 import PdfReader
from io import BytesIO
from PIL import Image
import pytesseract

# Carpeta con comprobantes
comprobantes_dir = Path("comprobantes")  # <-- cambialo a tu carpeta

# Carpeta para guardar textos extraídos
output_dir = Path("texts_output")
output_dir.mkdir(exist_ok=True)

def extract_text(file_path):
    ext = file_path.suffix.lower().lstrip('.')
    if ext == "pdf":
        with open(file_path, "rb") as f:
            reader = PdfReader(BytesIO(f.read()))
            texto = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    texto += page_text + "\n"
        return texto
    elif ext in {"png", "jpg", "jpeg", "bmp", "webp"}:
        img = Image.open(file_path)
        texto = pytesseract.image_to_string(img)
        return texto
    else:
        raise Exception(f"Extensión no soportada: {ext}")

for archivo in comprobantes_dir.iterdir():
    if archivo.is_file():
        try:
            texto = extract_text(archivo)
            output_file = output_dir / f"{archivo.stem}.txt"
            with open(output_file, "w", encoding="utf-8") as f_out:
                f_out.write(texto)
            print(f"Texto extraído guardado en {output_file}")
        except Exception as e:
            print(f"Error extrayendo texto de {archivo.name}: {e}")
