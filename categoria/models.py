from django.db import models


class Categoria(models.Model):
    class Tipo(models.TextChoices):
        DESPESA = 'despesa', 'Despesa'
        RECEITA = 'receita', 'Receita'
        AMBOS = 'ambos', 'Ambos'

    nome = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.DESPESA)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'categorias'
        ordering = ['nome']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.nome


class RegraCategorizacao(models.Model):
    """Regra usada pelo leitor_fatura para sugerir uma Categoria a partir do
    texto do lançamento importado (descrição ou categoria crua do banco)."""

    class Banco(models.TextChoices):
        NUBANK = 'nubank', 'Nubank'
        C6 = 'c6', 'C6 Bank'
        XP = 'xp', 'XP'

    padrao = models.CharField(
        max_length=100,
        help_text='Texto buscado (sem diferenciar maiúsculas/minúsculas) na descrição '
                   'ou na categoria vinda do banco.',
    )
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='regras')
    banco = models.CharField(
        max_length=10, choices=Banco.choices, blank=True,
        help_text='Deixe em branco para aplicar a regra em qualquer banco.',
    )
    prioridade = models.PositiveSmallIntegerField(
        default=0, help_text='Regras com prioridade maior são avaliadas primeiro.',
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'regras_categorizacao'
        ordering = ['-prioridade', 'padrao']
        verbose_name = 'Regra de categorização'
        verbose_name_plural = 'Regras de categorização'

    def __str__(self):
        return f'{self.padrao} → {self.categoria}'
