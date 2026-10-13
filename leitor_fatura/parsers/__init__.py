from .base import LancamentoBruto, LeitorFaturaBase
from .c6 import LeitorC6
from .nubank import LeitorNubank
from .xp import LeitorXP

LEITORES = [LeitorNubank, LeitorC6, LeitorXP]

__all__ = ['LancamentoBruto', 'LeitorFaturaBase', 'LeitorNubank', 'LeitorC6', 'LeitorXP', 'LEITORES']


def detectar_leitor(cabecalho: str):
    for leitor_cls in LEITORES:
        if leitor_cls.identifica(cabecalho):
            return leitor_cls
    return None
