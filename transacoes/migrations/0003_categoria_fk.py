# Segundo passo: cria a coluna categoria (FK) em paralelo à categoria_texto antiga,
# ainda vazia — a migração de dados (0004) é quem preenche.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categoria', '0001_initial'),
        ('transacoes', '0002_novos_campos'),
    ]

    operations = [
        migrations.AddField(
            model_name='transacao',
            name='categoria',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='transacoes', to='categoria.categoria',
            ),
        ),
    ]
