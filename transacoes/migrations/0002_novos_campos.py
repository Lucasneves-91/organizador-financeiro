# Primeiro passo da migração de Transacao: adiciona os campos novos e renomeia a
# coluna 'categoria' atual (texto livre) para 'categoria_texto', preservando o dado
# até a migração de dados (0004) linkar cada transação à Categoria correspondente.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transacoes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transacao',
            name='banco',
            field=models.CharField(blank=True, choices=[('nubank', 'Nubank'), ('c6', 'C6 Bank'), ('manual', 'Lançamento manual')], max_length=10),
        ),
        migrations.AddField(
            model_name='transacao',
            name='hash_importacao',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='transacao',
            name='natureza',
            field=models.CharField(blank=True, choices=[('fixo', 'Fixo'), ('variavel', 'Variável'), ('investimento', 'Investimento')], max_length=15),
        ),
        migrations.AddField(
            model_name='transacao',
            name='parcela_atual',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transacao',
            name='parcela_total',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transacao',
            name='valor_total',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.RenameField(
            model_name='transacao',
            old_name='categoria',
            new_name='categoria_texto',
        ),
    ]
