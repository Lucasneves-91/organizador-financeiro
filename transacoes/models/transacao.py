from django.db import models


class Transacao(models.Model):
    class Tipo(models.TextChoices):
        RECEITA = 'receita', 'Receita'
        DESPESA = 'despesa', 'Despesa'

    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    data = models.DateField()

    class Meta:
        db_table = 'transacoes'
        ordering = ['-data']

    def __str__(self):
        return f'{self.descricao} ({self.tipo})'
