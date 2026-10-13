import csv
import io
from datetime import datetime
from decimal import Decimal

from transacoes.models import Transacao

from .base import LancamentoBruto, LeitorFaturaBase


class LeitorC6(LeitorFaturaBase):
    banco = Transacao.Banco.C6

    @classmethod
    def identifica(cls, cabecalho: str) -> bool:
        colunas = [c.strip().lower() for c in cabecalho.strip().split(';')]
        esperado = ['data de compra', 'nome no cartão', 'final do cartão', 'categoria', 'descrição']
        return colunas[:5] == esperado

    def ler(self, conteudo: str) -> list[LancamentoBruto]:
        leitor = csv.DictReader(io.StringIO(conteudo), delimiter=';')
        lancamentos = []
        for linha in leitor:
            data_compra = linha.get('Data de Compra', '').strip()
            if not data_compra:
                continue

            data = datetime.strptime(data_compra, '%d/%m/%Y').date()
            descricao = linha['Descrição'].strip()
            categoria_crua = linha.get('Categoria', '').strip()
            if categoria_crua == '-':
                categoria_crua = ''

            parcela_atual, parcela_total = self._parcela(linha.get('Parcela', ''))
            valor_bruto = Decimal(linha['Valor (em R$)'].strip())

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
                categoria_crua=categoria_crua,
            ))
        return lancamentos

    @staticmethod
    def _parcela(valor: str):
        valor = valor.strip()
        if not valor or valor.lower() in ('única', 'unica'):
            return None, None
        if '/' not in valor:
            return None, None
        atual, total = valor.split('/', 1)
        return int(atual), int(total)
