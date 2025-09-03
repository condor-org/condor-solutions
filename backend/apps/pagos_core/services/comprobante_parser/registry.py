"""
Registro de extractores por banco.
"""
from . import generic
from .banks import (
    bbva, macro, galicia, mercadopago,
    cuentadni, naranjax, consultoramutual,
    quikipay, allaria
)

EXTRACTORS = [bbva, macro, galicia, mercadopago,
              cuentadni, naranjax, consultoramutual,
              quikipay, allaria]

def find_extractor(texto: str):
    for mod in EXTRACTORS:
        if mod.matches(texto):
            return mod
    return None
