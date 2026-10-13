# Segundo passo: lotes que já existem (importados antes dessa mudança) recebem o
# mês/ano de referência a partir de quando foram criados — que já era, na prática,
# "o mês em que a fatura foi importada".

from django.db import migrations


def preencher_referencia(apps, schema_editor):
    ImportacaoLote = apps.get_model('leitor_fatura', 'ImportacaoLote')
    for lote in ImportacaoLote.objects.all():
        lote.mes_referencia = lote.criado_em.month
        lote.ano_referencia = lote.criado_em.year
        lote.save(update_fields=['mes_referencia', 'ano_referencia'])


def reverter(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('leitor_fatura', '0002_referencia_e_duplicidade_valor'),
    ]

    operations = [
        migrations.RunPython(preencher_referencia, reverter),
    ]
