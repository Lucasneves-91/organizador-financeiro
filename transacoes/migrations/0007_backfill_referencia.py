# Segundo passo: preenche mes_referencia/ano_referencia pros dados que já existiam.
# Lançamento manual (sem hash_importacao) usa o mês da própria data. Lançamento
# importado usa o mês em que o lote de importação foi criado — era, na prática, "o
# mês em que a fatura foi importada", só não ficava salvo explicitamente antes.

from django.db import migrations


def preencher_referencia(apps, schema_editor):
    Transacao = apps.get_model('transacoes', 'Transacao')
    LancamentoImportado = apps.get_model('leitor_fatura', 'LancamentoImportado')

    lotes_por_transacao = {
        item.transacao_id: item.lote
        for item in LancamentoImportado.objects.exclude(transacao_id__isnull=True).select_related('lote')
    }

    for transacao in Transacao.objects.all():
        lote = lotes_por_transacao.get(transacao.id)
        if lote:
            transacao.mes_referencia = lote.criado_em.month
            transacao.ano_referencia = lote.criado_em.year
        else:
            transacao.mes_referencia = transacao.data.month
            transacao.ano_referencia = transacao.data.year
        transacao.save(update_fields=['mes_referencia', 'ano_referencia'])


def reverter(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('transacoes', '0006_referencia_nullable'),
        ('leitor_fatura', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(preencher_referencia, reverter),
    ]
