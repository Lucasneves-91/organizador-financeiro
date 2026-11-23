from decimal import Decimal

from django.db import models


class TipoMeta(models.TextChoices):
    VALOR = 'valor', 'R$'
    PERCENTUAL = 'percentual', '%'


def _descrever(tipo, valor, sufixo_valor, sufixo_percentual):
    if tipo == TipoMeta.PERCENTUAL:
        return f'{valor.normalize():f}'.replace('.', ',') + f'% {sufixo_percentual}'
    texto = f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {texto} {sufixo_valor}'


class MetaEconomia(models.Model):
    """Meta anual de economia: valor fixo (R$) ou % da receita do ano."""

    Tipo = TipoMeta

    ano = models.PositiveSmallIntegerField(unique=True)
    tipo_anual = models.CharField(max_length=10, choices=TipoMeta.choices, default=TipoMeta.VALOR)
    valor_anual = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'meta anual de economia'
        verbose_name_plural = 'metas anuais de economia'

    def __str__(self):
        return f'Meta {self.ano}'

    @property
    def tem_anual(self) -> bool:
        return self.valor_anual is not None

    def valor_do_ano(self, receita_ano: Decimal) -> Decimal:
        if self.tipo_anual == TipoMeta.PERCENTUAL:
            return receita_ano * self.valor_anual / 100
        return self.valor_anual

    def descricao_anual(self) -> str:
        return _descrever(self.tipo_anual, self.valor_anual, 'no ano', 'da receita do ano')


class MetaMensal(models.Model):
    """Meta de economia de um mês específico: valor fixo (R$) ou % da receita do mês."""

    Tipo = TipoMeta

    ano = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    tipo = models.CharField(max_length=10, choices=TipoMeta.choices, default=TipoMeta.VALOR)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'meta mensal de economia'
        verbose_name_plural = 'metas mensais de economia'
        constraints = [
            models.UniqueConstraint(fields=['ano', 'mes'], name='meta_mensal_unica_por_mes'),
        ]
        ordering = ['ano', 'mes']

    def __str__(self):
        return f'Meta {self.mes:02d}/{self.ano}'

    def valor_do_mes(self, receita_mes: Decimal) -> Decimal:
        if self.tipo == TipoMeta.PERCENTUAL:
            return receita_mes * self.valor / 100
        return self.valor
