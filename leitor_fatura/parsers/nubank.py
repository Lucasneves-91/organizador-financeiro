import csv
import io
import re
from datetime import date
from decimal import Decimal

from transacoes.models import Transacao

from .base import LancamentoBruto, LeitorFaturaBase

PADRAO_PARCELA = re.compile(r'^(.*?)\s*-\s*Parcela\s+(\d+)/(\d+)\s*$', re.IGNORECASE)


def _converter_valor(bruto: str) -> Decimal:
    """Converte "417,16" ou "- 1.492,58" (formato Nubank: milhar com ponto,
    decimal com vírgula, sinal de menos pode vir separado por espaço) em Decimal."""
    texto = bruto.strip().replace(' ', '')
    negativo = texto.startswith('-')
    texto = texto.lstrip('-')
    texto = texto.replace('.', '').replace(',', '.')
    valor = Decimal(texto)
    return -valor if negativo else valor


class LeitorNubank(LeitorFaturaBase):
    banco = Transacao.Banco.NUBANK

    @classmethod
    def identifica(cls, cabecalho: str) -> bool:
        colunas = [c.strip().lower() for c in cabecalho.strip().split(',')]
        return colunas[:3] == ['date', 'title', 'amount']

    def ler(self, conteudo: str) -> list[LancamentoBruto]:
        leitor = csv.DictReader(io.StringIO(conteudo))
        lancamentos = []
        for linha in leitor:
            if not linha.get('date'):
                continue

            data = date.fromisoformat(linha['date'].strip())
            valor_bruto = _converter_valor(linha['amount'])
            titulo = linha['title'].strip()

            match = PADRAO_PARCELA.match(titulo)
            if match:
                descricao, parcela_atual, parcela_total = match.group(1), int(match.group(2)), int(match.group(3))
            else:
                descricao, parcela_atual, parcela_total = titulo, None, None

            if valor_bruto < 0:
                tipo = Transacao.Tipo.RECEITA
                valor = -valor_bruto
            else:
                tipo = Transacao.Tipo.DESPESA
                valor = valor_bruto

            lancamentos.append(LancamentoBruto(
                data=data,
                descricao=descricao,
                valor=valor,
                tipo=tipo,
                banco=self.banco,
                parcela_atual=parcela_atual,
                parcela_total=parcela_total,
                categoria_crua='',
            ))
        return lancamentos
