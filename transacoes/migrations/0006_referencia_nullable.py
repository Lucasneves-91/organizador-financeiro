# Primeiro passo: adiciona mes_referencia/ano_referencia (mês de competência) como
# nullable — a próxima migração faz o backfill a partir dos dados existentes.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transacoes', '0005_remover_categoria_texto'),
    ]

    operations = [
        migrations.AddField(
            model_name='transacao',
            name='mes_referencia',
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='transacao',
            name='ano_referencia',
            field=models.PositiveSmallIntegerField(null=True),
        ),
    ]
