import csv
import io
import re
from datetime import datetime
from decimal import Decimal

from transacoes.models import Transacao

from .base import LancamentoBruto, LeitorFaturaBase

PADRAO_PARCELA = re.compile(r'(\d+)\s*de\s*(\d+)')


def _converter_valor(bruto: str) -> Decimal:
    """Converte "R$ 58,46" ou "R$ -2.556,60" (formato XP: prefixo R$, milhar com
    ponto, decimal com vírgula) em Decimal."""
    texto = bruto.replace('R$', '').strip().replace(' ', '')
    negativo = texto.startswith('-')
    texto = texto.lstrip('-')
    texto = texto.replace('.', '').replace(',', '.')
    valor = Decimal(texto)
    return -valor if negativo else valor


class LeitorXP(LeitorFaturaBase):
    banco = Transacao.Banco.XP

    @classmethod
    def identifica(cls, cabecalho: str) -> bool:
        colunas = [c.strip().lower() for c in cabecalho.strip().split(';')]
        return colunas[:5] == ['data', 'estabelecimento', 'portador', 'valor', 'parcela']

    def ler(self, conteudo: str) -> list[LancamentoBruto]:
        leitor = csv.DictReader(io.StringIO(conteudo), delimiter=';')
        lancamentos = []
        for linha in leitor:
            data_str = linha.get('Data', '').strip()
            if not data_str:
                continue

            data = datetime.strptime(data_str, '%d/%m/%Y').date()
            descricao = linha['Estabelecimento'].strip()
            valor_bruto = _converter_valor(linha['Valor'])

            # "1 de 2" -> parcelado; "-" ou " de 1" (sem número antes do "de") -> à vista.
            match = PADRAO_PARCELA.search(linha.get('Parcela', ''))
            if match:
                parcela_atual, parcela_total = int(match.group(1)), int(match.group(2))
            else:
                parcela_atual, parcela_total = None, None

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
