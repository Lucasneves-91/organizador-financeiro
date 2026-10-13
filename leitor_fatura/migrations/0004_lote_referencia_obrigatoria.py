# Último passo: agora que todo lote tem mes/ano_referencia preenchido, torna os
# campos obrigatórios (igual ao model).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leitor_fatura', '0003_backfill_lote_referencia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importacaolote',
            name='mes_referencia',
            field=models.PositiveSmallIntegerField(),
        ),
        migrations.AlterField(
            model_name='importacaolote',
            name='ano_referencia',
            field=models.PositiveSmallIntegerField(),
        ),
        migrations.AlterField(
            model_name='lancamentoimportado',
            name='duplicado_valor_descricao',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
