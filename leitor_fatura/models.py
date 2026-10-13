from django.db import models

from transacoes.models import Transacao


class ImportacaoLote(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        CONFIRMADO = 'confirmado', 'Confirmado'
        CANCELADO = 'cancelado', 'Cancelado'

    arquivo_nome = models.CharField(max_length=255)
    banco = models.CharField(max_length=10, choices=Transacao.Banco.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    criado_em = models.DateTimeField(auto_now_add=True)

    # Mês/ano de competência que vai ser gravado em todas as Transacao desse lote —
    # é o mês em que a fatura foi importada, não a data de cada compra.
    mes_referencia = models.PositiveSmallIntegerField()
    ano_referencia = models.PositiveSmallIntegerField()

    class Meta:
        db_table = 'importacao_lotes'
        ordering = ['-criado_em']
        verbose_name = 'Lote de importação'
        verbose_name_plural = 'Lotes de importação'

    def __str__(self):
        return f'{self.arquivo_nome} ({self.get_banco_display()}, {self.get_status_display()})'


class LancamentoImportado(models.Model):
    lote = models.ForeignKey(ImportacaoLote, on_delete=models.CASCADE, related_name='lancamentos')

    data = models.DateField()
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=Transacao.Tipo.choices)
    parcela_atual = models.PositiveSmallIntegerField(null=True, blank=True)
    parcela_total = models.PositiveSmallIntegerField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    categoria_crua = models.CharField(max_length=150, blank=True)
    hash_importacao = models.CharField(max_length=64)

    categoria_sugerida = models.ForeignKey(
        'categoria.Categoria', on_delete=models.SET_NULL, null=True, blank=True,
    )
    selecionado = models.BooleanField(default=True)

    # Duplicata "exata": esse mesmo lançamento já foi importado antes (mesmo hash).
    duplicado = models.BooleanField(default=False)

    # Duplicata "por valor": já existe outra Transacao (manual ou importada) com o
    # mesmo valor no mesmo mês de referência — só um aviso, não exclui sozinho.
    duplicado_valor = models.BooleanField(default=False)
    duplicado_valor_descricao = models.CharField(max_length=255, blank=True)

    transacao = models.ForeignKey(
        Transacao, on_delete=models.SET_NULL, null=True, blank=True, related_name='origem_importacao',
    )

    class Meta:
        db_table = 'lancamentos_importados'
        ordering = ['-data']

    def __str__(self):
        return f'{self.descricao} ({self.data})'
