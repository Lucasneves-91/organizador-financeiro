from decimal import Decimal

from django.db import migrations


def preencher_valor_dividido(apps, schema_editor):
    Transacao = apps.get_model('transacoes', 'Transacao')
    for transacao in Transacao.objects.exclude(dividido=''):
        if transacao.dividido == 'metade':
            transacao.valor_dividido = transacao.valor / 2
        elif transacao.dividido == 'quarenta':
            transacao.valor_dividido = transacao.valor * Decimal('0.4')
        else:
            continue
        transacao.save(update_fields=['valor_dividido'])


class Migration(migrations.Migration):

    dependencies = [
        ('transacoes', '0016_transacao_valor_dividido'),
    ]

    operations = [
        migrations.RunPython(preencher_valor_dividido, migrations.RunPython.noop),
    ]
