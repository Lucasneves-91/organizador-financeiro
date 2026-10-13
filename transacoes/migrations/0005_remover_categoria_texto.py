# Último passo: agora que todo mundo está linkado pela FK, remove a coluna de
# texto livre antiga.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transacoes', '0004_migrar_categoria_texto'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transacao',
            name='categoria_texto',
        ),
    ]
