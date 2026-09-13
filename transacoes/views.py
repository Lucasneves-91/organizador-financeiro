from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from .forms import TransacaoForm
from .helpers.formatadores import formatar_valor_monetario
from .services.transacao_service import TransacaoService


def lista(request):
    transacoes = TransacaoService.listar()
    totais = TransacaoService.obter_totais()
    despesas_por_categoria = TransacaoService.obter_despesas_por_categoria()

    for indice, linha in enumerate(despesas_por_categoria):
        linha['cor'] = f'cor-{indice % 8 + 1}'
        linha['total_formatado'] = formatar_valor_monetario(linha['total'])

    contexto = {
        'transacoes': transacoes,
        'total_receitas': formatar_valor_monetario(totais['total_receitas']),
        'total_despesas': formatar_valor_monetario(totais['total_despesas']),
        'saldo': formatar_valor_monetario(totais['saldo']),
        'saldo_positivo': totais['saldo'] >= 0,
        'percentual_receitas': totais['percentual_receitas'],
        'percentual_despesas': totais['percentual_despesas'],
        'percentual_economia': totais['percentual_economia'],
        'despesas_por_categoria': despesas_por_categoria,
    }
    return render(request, 'transacoes/lista.html', contexto)


def cadastrar(request):
    if request.method == 'POST':
        form = TransacaoForm(request.POST)
        if form.is_valid():
            try:
                TransacaoService.criar(**form.cleaned_data)
                return redirect('transacoes:lista')
            except ValidationError as erro:
                form.add_error(None, erro)
    else:
        form = TransacaoForm()
    return render(request, 'transacoes/form.html', {'form': form, 'titulo': 'Nova transação'})


def editar(request, transacao_id):
    transacao = TransacaoService.buscar(transacao_id)
    if request.method == 'POST':
        form = TransacaoForm(request.POST, instance=transacao)
        if form.is_valid():
            try:
                TransacaoService.editar(transacao_id, **form.cleaned_data)
                return redirect('transacoes:lista')
            except ValidationError as erro:
                form.add_error(None, erro)
    else:
        form = TransacaoForm(instance=transacao)
    return render(request, 'transacoes/form.html', {'form': form, 'titulo': 'Editar transação'})


def excluir(request, transacao_id):
    transacao = TransacaoService.buscar(transacao_id)
    if request.method == 'POST':
        TransacaoService.excluir(transacao_id)
        return redirect('transacoes:lista')
    return render(request, 'transacoes/confirmar_exclusao.html', {'transacao': transacao})
