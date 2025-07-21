#backend/tests/test_comprobantes_validacion.py
import os
import yaml
import pytest
from pathlib import Path
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from apps.turnos_core.models import Turno, Servicio
from apps.pagos_core.models import ConfiguracionPago
from apps.pagos_core.services.comprobantes import ComprobanteService

ruta_base = Path(__file__).resolve().parent.parent / "comprobantes"

with open(ruta_base / "comprobantes-datos-confirmacion.yaml", "r") as f:
    raw = yaml.safe_load(f)

casos_comprobantes = {
    item["archivo"]: item["esperado"]
    for item in raw
}


@pytest.fixture
def usuario_dummy(db):
    User = get_user_model()
    return User.objects.create_user(
        email="dummy@example.com",
        password="pass1234",
        username="dummy"
    )


@pytest.fixture
def turno_dummy(db, usuario_dummy):
    servicio = Servicio.objects.create(nombre="test", lugar=None)
    ct = ContentType.objects.get_for_model(Servicio)
    turno = Turno.objects.create(
        fecha=timezone.now().date(),
        hora=timezone.now().time(),
        servicio=servicio,
        content_type=ct,
        object_id=servicio.id,
        lugar=None,
        usuario=usuario_dummy
    )
    return turno


@pytest.mark.parametrize("archivo, esperado", casos_comprobantes.items())
def test_validacion_comprobante(db, usuario_dummy, turno_dummy, archivo, esperado):
    # Configuración del pago para este caso
    ConfiguracionPago.objects.all().delete()
    ConfiguracionPago.objects.create(
        destinatario="Test",
        cbu=esperado.get("cbu_destino", ""),
        alias=esperado.get("alias", "") or esperado.get("alias_destino", ""),
        monto_esperado=esperado["monto"],
        tiempo_maximo_minutos=1500000
    )

    # Cargar archivo con fallback a .jpeg
    path = ruta_base / archivo
    if not path.exists():
        alt = archivo.rsplit(".", 1)[0] + ".jpeg"
        alt_path = ruta_base / alt
        if alt_path.exists():
            path = alt_path
        else:
            pytest.fail(f"No encontré ni {archivo} ni {alt} en {ruta_base}")

    with open(path, "rb") as f:
        file_obj = SimpleUploadedFile(path.name, f.read())

    # Extraer y mostrar el texto para debug
    texto = ComprobanteService._extract_text(file_obj)
    print(f"\n--- Texto extraído de {archivo} ---\n{texto}\n{'-'*50}")

    # Subir comprobante
    try:
        comprobante = ComprobanteService.upload_comprobante(
            turno_id=turno_dummy.id,
            file_obj=file_obj,
            usuario=usuario_dummy
        )
    except ValidationError as e:
        pytest.fail(f"Subida de {archivo} falló inesperadamente: {e}")

    datos = comprobante.datos_extraidos

    # Validaciones claras
    assert "monto" in datos and datos["monto"] is not None, \
        f"{archivo}: No se extrajo monto. Datos: {datos}"
    assert abs(datos["monto"] - esperado["monto"]) < 0.01, \
        f"{archivo}: Monto esperado {esperado['monto']} vs extraído {datos['monto']}"

    cbu_esperado = esperado.get("cbu_destino")
    alias_esperado = esperado.get("alias") or esperado.get("alias_destino")
    cbu_extraido = datos.get("cbu_destino")
    alias_extraido = datos.get("alias")

    cbu_ok = cbu_esperado and cbu_esperado == cbu_extraido
    alias_ok = alias_esperado and alias_esperado == alias_extraido

    assert cbu_ok or alias_ok, (
        f"{archivo}: No extrajo cbu/alias correcto.\n"
        f"Esperado CBU: {cbu_esperado}, extraído: {cbu_extraido}\n"
        f"Esperado Alias: {alias_esperado}, extraído: {alias_extraido}\n"
        f"Datos completos: {datos}"
    )
