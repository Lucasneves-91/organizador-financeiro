from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class LancamentoBruto:
    """Um lançamento extraído de um arquivo de fatura/extrato, antes de virar Transacao."""

    data: date
    descricao: str
    valor: Decimal
    tipo: str  # 'receita' ou 'despesa', ver Transacao.Tipo
    banco: str  # ver Transacao.Banco
    parcela_atual: Optional[int] = None
    parcela_total: Optional[int] = None
    categoria_crua: str = ''  # categoria como veio do banco, se o banco mandar

    @property
    def valor_total(self) -> Optional[Decimal]:
        if self.parcela_total and self.parcela_total > 0:
            return (self.valor * self.parcela_total).quantize(Decimal('0.01'))
        return None


class LeitorFaturaBase:
    """Classe-base para um leitor de arquivo de um banco específico.

    Cada banco exporta CSV com estrutura diferente (separador, colunas, formato de
    valor/data), então cada um ganha sua própria subclasse. A detecção de qual leitor
    usar é feita pelo cabeçalho (primeira linha) do arquivo.
    """

    banco: str = ''

    @classmethod
    def identifica(cls, cabecalho: str) -> bool:
        raise NotImplementedError

    def ler(self, conteudo: str) -> list[LancamentoBruto]:
        raise NotImplementedError
