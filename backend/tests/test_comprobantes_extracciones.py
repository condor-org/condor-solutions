import pytest
from datetime import datetime
from apps.pagos_core.services.comprobantes import ComprobanteService

@pytest.mark.parametrize(
    "texto,monto_esperado",
    [
        ("Pago realizado por $ 1.234,56 en la cuenta", 1234.56),
        ("El monto es $12.345,67", 12345.67),
        ("Monto total: $1234.56", 1234.56),
        ("No hay monto aquí", None),
        ("Monto mal $1,23,45", None),
    ],
)
def test_extract_monto(texto, monto_esperado):
    monto = ComprobanteService._extract_monto(texto)
    if monto_esperado is None:
        assert monto is None
    else:
        assert abs(monto - monto_esperado) < 0.01

@pytest.mark.parametrize(
    "texto,fecha_esperada",
    [
        ("Fecha de pago 01/07/2025", datetime(2025, 7, 1)),
        ("El pago fue hecho el 15-12-2024", datetime(2024, 12, 15)),
        ("No hay fecha", None),
        ("2025-03-10 es la fecha", datetime(2025, 3, 10)),
    ],
)
def test_extract_fecha(texto, fecha_esperada):
    fecha = ComprobanteService._extract_fecha(texto)
    if fecha_esperada is None:
        assert fecha is None
    else:
        assert fecha.year == fecha_esperada.year
        assert fecha.month == fecha_esperada.month
        assert fecha.day == fecha_esperada.day

@pytest.mark.parametrize(
    "texto,cbu_esperado,alias_esperado",
    [
        ("Destinatario CBU 0000003100072077739741 alias ALIAS1", "0000003100072077739741", "ALIAS1"),
        ("Cuenta destino: 0000003100072077739741", "0000003100072077739741", None),
        ("Alias destinatario: ALIAS2", None, "ALIAS2"),
        ("No hay datos", None, None),
    ],
)
def test_extract_cbu_alias_destinatario(texto, cbu_esperado, alias_esperado):
    cbu, alias = ComprobanteService._extract_cbu_alias_destinatario(texto)
    assert cbu == cbu_esperado
    assert alias == alias_esperado


@pytest.mark.parametrize(
    "texto, alias_esperado",
    [
        ("Alias: alias.correcto1", "alias.correcto1"),
        ("alias: alias-con-guion", "alias-con-guion"),
        ("ALIAS: alias.con.puntos", "alias.con.puntos"),
        ("alias: corto", None),  # menos de 6 caracteres, no debe capturar
        ("alias: aliasdemasiadolargexxxxx", None),  # más de 20 caracteres, no debe capturar
        ("Alias: alias_valido", None),  # _ no permitido, no debe capturar
        ("Texto sin alias", None),
    ],
)
def test_extract_alias_reglamentario(texto, alias_esperado):
    _, alias = ComprobanteService._extract_cbu_alias_destinatario(texto)
    assert alias == alias_esperado

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Importe a transferir: $ 2,420,000.00", 2420000.00),
        ("Importe: $ 2.420.000,00", 2420000.00),
        ("Monto total $1,234.56", 1234.56),
        ("Monto total $1.234,56", 1234.56),
        ("$ 1234,56", 1234.56),
        ("$1,234,567", 1234567.0),
        ("$1.234.567", 1234567.0),
        ("$1234567", 1234567.0),
        ("Importe a transferir: $ 1,234", 1234.0),
        ("Importe: $ 1.234", 1234.0),
        ("El monto es $ 1234", 1234.0),
        ("Sin monto aquí", None),
        ("Importe a transferir: $ 1.234.567,89", 1234567.89),
        ("Importe a transferir: $ 1,234,567.89", 1234567.89),
        ("Importe a transferir: $ 1.234", 1234.0),
        ("Importe a transferir: $ 1,234", 1234.0),
    ]
)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Razon Social Importe Ng Technologies S.r.l. $ 700.000,00", 700000.0),
        ("Importe total $ 10.000.000,00", 10000000.0),
        ("Datos de la Operación Importe $ 2,420,000.00", 2420000.0),
        ("Monto: $ 882.000,00", 882000.0),
        ("Importe $ 51.400,00", 51400.0),
        ("Detalle Importe 317.000,00", 317000.0),
        ("$ 6,00", 6.0),
        ("$ 14.000", 14000.0),
    ]
)
def test_extract_monto_varios_formatos(texto, esperado):
    monto = ComprobanteService._extract_monto(texto)
    if esperado is None:
        assert monto is None
    else:
        assert abs(monto - esperado) < 0.01
