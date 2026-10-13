# Primeiro passo: adiciona os campos novos. mes/ano_referencia do lote ficam
# nullable por enquanto — a migração seguinte faz o backfill a partir de criado_em.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leitor_fatura', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='importacaolote',
            name='mes_referencia',
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='importacaolote',
            name='ano_referencia',
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='lancamentoimportado',
            name='duplicado_valor',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='lancamentoimportado',
            name='duplicado_valor_descricao',
            field=models.CharField(blank=True, max_length=255, default=''),
        ),
    ]
