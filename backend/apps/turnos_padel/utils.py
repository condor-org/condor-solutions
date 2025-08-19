# apps/turnos_padel/utils.py

def proximo_mes(anio: int, mes: int) -> tuple[int, int]:
    """
    Devuelve el (año, mes) del mes siguiente.
    Ej: (2025, 8) → (2025, 9), (2025, 12) → (2026, 1)
    """
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)



