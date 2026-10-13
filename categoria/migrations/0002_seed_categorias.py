# Categorias de despesa iniciais, só pra não começar com a tela vazia — baseadas
# na planilha que o usuário já usava. Livres pra editar/excluir depois.

from django.db import migrations

CATEGORIAS_INICIAIS = [
    'Lazer', 'Automóvel', 'Vestuário', 'Despesas Pessoais',
    'Presente', 'Saúde', 'Habitação', 'Princesa', 'Dividido',
]


def criar_categorias_iniciais(apps, schema_editor):
    Categoria = apps.get_model('categoria', 'Categoria')
    for nome in CATEGORIAS_INICIAIS:
        Categoria.objects.get_or_create(nome=nome, defaults={'tipo': 'despesa'})


def remover_categorias_iniciais(apps, schema_editor):
    Categoria = apps.get_model('categoria', 'Categoria')
    Categoria.objects.filter(nome__in=CATEGORIAS_INICIAIS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('categoria', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(criar_categorias_iniciais, remover_categorias_iniciais),
    ]
