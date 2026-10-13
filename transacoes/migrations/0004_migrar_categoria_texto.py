# Terceiro passo: converte os valores de texto livre que já existiam em
# categoria_texto para registros de Categoria (uma por valor distinto) e liga
# cada Transacao à Categoria correspondente pela nova FK.

from django.db import migrations


def migrar_categorias(apps, schema_editor):
    Transacao = apps.get_model('transacoes', 'Transacao')
    Categoria = apps.get_model('categoria', 'Categoria')

    nomes = (
        Transacao.objects.exclude(categoria_texto__isnull=True)
        .exclude(categoria_texto__exact='')
        .values_list('categoria_texto', flat=True)
        .distinct()
    )

    for nome in nomes:
        tipos = set(Transacao.objects.filter(categoria_texto=nome).values_list('tipo', flat=True))
        if tipos == {'receita'}:
            tipo_categoria = 'receita'
        elif tipos == {'despesa'}:
            tipo_categoria = 'despesa'
        else:
            tipo_categoria = 'ambos'

        categoria, _ = Categoria.objects.get_or_create(nome=nome, defaults={'tipo': tipo_categoria})
        Transacao.objects.filter(categoria_texto=nome).update(categoria=categoria)


def reverter_categorias(apps, schema_editor):
    Transacao = apps.get_model('transacoes', 'Transacao')
    for transacao in Transacao.objects.exclude(categoria__isnull=True).select_related('categoria'):
        Transacao.objects.filter(pk=transacao.pk).update(categoria_texto=transacao.categoria.nome)


class Migration(migrations.Migration):

    dependencies = [
        ('transacoes', '0003_categoria_fk'),
    ]

    operations = [
        migrations.RunPython(migrar_categorias, reverter_categorias),
    ]
