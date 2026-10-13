from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoriaForm, RegraCategorizacaoForm
from .models import Categoria, RegraCategorizacao


def lista_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, 'categoria/categorias_lista.html', {'categorias': categorias})


def cadastrar_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('categoria:lista_categorias')
    else:
        form = CategoriaForm()
    return render(request, 'categoria/categoria_form.html', {'form': form, 'titulo': 'Nova categoria'})


def editar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            return redirect('categoria:lista_categorias')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'categoria/categoria_form.html', {'form': form, 'titulo': 'Editar categoria'})


def excluir_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    if request.method == 'POST':
        categoria.delete()
        return redirect('categoria:lista_categorias')
    return render(request, 'categoria/categoria_confirmar_exclusao.html', {'categoria': categoria})


def lista_regras(request):
    regras = RegraCategorizacao.objects.select_related('categoria').all()
    return render(request, 'categoria/regras_lista.html', {'regras': regras})


def cadastrar_regra(request):
    if request.method == 'POST':
        form = RegraCategorizacaoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('categoria:lista_regras')
    else:
        form = RegraCategorizacaoForm()
    return render(request, 'categoria/regra_form.html', {'form': form, 'titulo': 'Nova regra de categorização'})


def editar_regra(request, regra_id):
    regra = get_object_or_404(RegraCategorizacao, pk=regra_id)
    if request.method == 'POST':
        form = RegraCategorizacaoForm(request.POST, instance=regra)
        if form.is_valid():
            form.save()
            return redirect('categoria:lista_regras')
    else:
        form = RegraCategorizacaoForm(instance=regra)
    return render(request, 'categoria/regra_form.html', {'form': form, 'titulo': 'Editar regra de categorização'})


def excluir_regra(request, regra_id):
    regra = get_object_or_404(RegraCategorizacao, pk=regra_id)
    if request.method == 'POST':
        regra.delete()
        return redirect('categoria:lista_regras')
    return render(request, 'categoria/regra_confirmar_exclusao.html', {'regra': regra})
