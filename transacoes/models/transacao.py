from django.db import models


class Transacao(models.Model):
    class Tipo(models.TextChoices):
        RECEITA = 'receita', 'Receita'
        DESPESA = 'despesa', 'Despesa'

    class Banco(models.TextChoices):
        NUBANK = 'nubank', 'Nubank'
        C6 = 'c6', 'C6 Bank'
        XP = 'xp', 'XP'
        MANUAL = 'manual', 'Lançamento manual'

    class Natureza(models.TextChoices):
        FIXO = 'fixo', 'Fixo'
        VARIAVEL = 'variavel', 'Variável'
        INVESTIMENTO = 'investimento', 'Investimento'

    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    categoria = models.ForeignKey(
        'categoria.Categoria', on_delete=models.SET_NULL, null=True, blank=True, related_name='transacoes',
    )
    data = models.DateField(verbose_name='data da compra', help_text='Data da compra/lançamento.')

    # Mês/ano em que a transação "conta" pro dashboard (competência). Pra lançamento
    # manual é igual ao mês de `data`; pra importado é o mês em que a fatura foi
    # importada — uma compra de agosto parcelada pode cair numa fatura de outubro.
    mes_referencia = models.PositiveSmallIntegerField()
    ano_referencia = models.PositiveSmallIntegerField()

    banco = models.CharField(max_length=10, choices=Banco.choices, blank=True)
    natureza = models.CharField(max_length=15, choices=Natureza.choices, blank=True)
    parcela_atual = models.PositiveSmallIntegerField(null=True, blank=True)
    parcela_total = models.PositiveSmallIntegerField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Preenchido apenas em lançamentos vindos de importação de fatura (leitor_fatura),
    # usado para não importar o mesmo lançamento duas vezes.
    hash_importacao = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'transacoes'
        ordering = ['-data']

    def __str__(self):
        return f'{self.descricao} ({self.tipo})'
