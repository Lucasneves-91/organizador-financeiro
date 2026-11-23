from decimal import Decimal

from django.db import models


class Transacao(models.Model):
    class Tipo(models.TextChoices):
        RECEITA = 'receita', 'Receita'
        DESPESA = 'despesa', 'Despesa'
        INVESTIMENTO = 'investimento', 'Investimento'

    class Banco(models.TextChoices):
        NUBANK = 'nubank', 'Nubank'
        C6 = 'c6', 'C6 Bank'
        XP = 'xp', 'XP'
        PIX = 'pix', 'PIX'
        CARTAO_PRINCESA = 'cartao_princesa', 'Cartao Princesa'
        MERCADO_LIVRE = 'mercado_livre', 'Mercado Livre'
        XP_INVESTIMENTO = 'xp_investimento', 'XP Investimento'
        MANUAL = 'manual', 'Lançamento manual'

    # Investimento soma junto com as despesas nos totais.
    TIPOS_SAIDA = [Tipo.DESPESA, Tipo.INVESTIMENTO]
    BANCOS_INVESTIMENTO = [Banco.MERCADO_LIVRE, Banco.XP_INVESTIMENTO, Banco.NUBANK]
    # Bancos que só fazem sentido para investimento (não aparecem em receita/despesa).
    BANCOS_SO_INVESTIMENTO = [Banco.MERCADO_LIVRE, Banco.XP_INVESTIMENTO]

    class Natureza(models.TextChoices):
        FIXO = 'fixo', 'Fixo'
        VARIAVEL = 'variavel', 'Variável'
        INVESTIMENTO = 'investimento', 'Investimento'

    class Dividido(models.TextChoices):
        METADE = 'metade', '50%'
        QUARENTA = 'quarenta', '40%'

    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    categoria = models.ForeignKey(
        'categoria.Categoria', on_delete=models.SET_NULL, null=True, blank=True, related_name='transacoes',
    )
    data = models.DateField(verbose_name='data da compra', help_text='Data da compra/lançamento.')

    # Mês/ano em que a transação "conta" pro dashboard (competência). Pra lançamento
    # manual é igual ao mês de `data`; pra importado é o mês em que a fatura foi
    # importada — uma compra de agosto parcelada pode cair numa fatura de outubro.
    mes_referencia = models.PositiveSmallIntegerField()
    ano_referencia = models.PositiveSmallIntegerField()

    banco = models.CharField(max_length=20, choices=Banco.choices, blank=True)
    natureza = models.CharField(max_length=15, choices=Natureza.choices, blank=True)
    parcela_atual = models.PositiveSmallIntegerField(null=True, blank=True)
    parcela_total = models.PositiveSmallIntegerField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dividido = models.CharField(max_length=10, choices=Dividido.choices, blank=True)
    # Começa com um valor sugerido conforme `dividido` (metade/40%), mas pode ser
    # sobrescrito à mão — por isso é campo, não só uma conta em cima de `valor`.
    valor_dividido = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    observacao = models.TextField(blank=True, verbose_name='observação')

    # Preenchido apenas em lançamentos vindos de importação de fatura (leitor_fatura),
    # usado para não importar o mesmo lançamento duas vezes.
    hash_importacao = models.CharField(max_length=64, unique=True, null=True, blank=True)

    # Parcelas da mesma compra compartilham o mesmo grupo. `parcela_gerada` marca as
    # parcelas futuras criadas automaticamente a partir de uma parcela lançada.
    grupo_parcelas = models.UUIDField(null=True, blank=True, db_index=True)
    parcela_gerada = models.BooleanField(default=False)

    class Meta:
        db_table = 'transacoes'
        ordering = ['-data']

    def __str__(self):
        return f'{self.descricao} ({self.tipo})'

    def proximas_parcelas(self):
        if not self.grupo_parcelas or not self.parcela_atual:
            return Transacao.objects.none()
        return Transacao.objects.filter(
            grupo_parcelas=self.grupo_parcelas, parcela_atual__gt=self.parcela_atual,
        ).exclude(pk=self.pk)

    def sugerir_valor_dividido(self):
        if self.dividido == self.Dividido.METADE:
            return self.valor / 2
        if self.dividido == self.Dividido.QUARENTA:
            return self.valor * Decimal('0.4')
        return None
