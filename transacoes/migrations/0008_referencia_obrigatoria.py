# Último passo: agora que toda Transacao tem mes/ano_referencia preenchido, torna
# os campos obrigatórios (igual ao model).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transacoes', '0007_backfill_referencia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transacao',
            name='mes_referencia',
            field=models.PositiveSmallIntegerField(),
        ),
        migrations.AlterField(
            model_name='transacao',
            name='ano_referencia',
            field=models.PositiveSmallIntegerField(),
        ),
    ]
