from datetime import date

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from categoria.models import Categoria
from transacoes.services.transacao_service import TransacaoService
from transacoes.views import NOMES_MESES

from .forms import UploadFaturaForm
from .models import ImportacaoLote
from .services import FormatoNaoReconhecido, ImportacaoService


def upload(request):
    if request.method == 'POST':
        form = UploadFaturaForm(request.POST, request.FILES)
        if form.is_valid():
            arquivos = form.cleaned_data['arquivos']
            if not isinstance(arquivos, list):
                arquivos = [arquivos]

            mes_referencia = form.cleaned_data['mes_referencia']
            ano_referencia = form.cleaned_data['ano_referencia']

            lotes_criados = []
            for arquivo in arquivos:
                try:
                    lotes_criados.append(
                        ImportacaoService.processar(arquivo, mes_referencia, ano_referencia)
                    )
                except FormatoNaoReconhecido as erro:
                    messages.error(request, f'{arquivo.name}: {erro}')
                except (UnicodeDecodeError, ValueError) as erro:
                    messages.error(request, f'{arquivo.name}: não consegui ler esse arquivo ({erro}).')

            if len(lotes_criados) == 1:
                return redirect('leitor_fatura:preview', lote_id=lotes_criados[0].id)
            if len(lotes_criados) > 1:
                messages.success(
                    request,
                    f'{len(lotes_criados)} fatura(s) carregada(s). Revise e confirme cada uma abaixo.',
                )
                return redirect('leitor_fatura:lista_faturas')
    else:
        # Pré-preenche com o mês/ano que estava selecionado no dashboard (link "Importar
        # fatura" manda ?mes=&ano=), senão com o mês/competência mais recente conhecido.
        mes_param = request.GET.get('mes')
        ano_param = request.GET.get('ano')
        if mes_param and ano_param:
            inicial = {'mes_referencia': int(mes_param), 'ano_referencia': int(ano_param)}
        else:
            hoje = date.today()
            mes, ano = TransacaoService.mes_ano_mais_recente() or (hoje.month, hoje.year)
            inicial = {'mes_referencia': mes, 'ano_referencia': ano}
        form = UploadFaturaForm(initial=inicial)
    return render(request, 'leitor_fatura/upload.html', {'form': form})


def preview(request, lote_id):
    lote = get_object_or_404(ImportacaoLote, pk=lote_id, status=ImportacaoLote.Status.PENDENTE)
    lancamentos = lote.lancamentos.select_related('categoria_sugerida').order_by('-data')
    categorias = Categoria.objects.filter(ativo=True)
    contexto = {
        'lote': lote,
        'lancamentos': lancamentos,
        'categorias': categorias,
        'total_duplicados': lancamentos.filter(duplicado=True).count(),
        'total_duplicados_valor': lancamentos.filter(duplicado_valor=True).count(),
        'mes_referencia_nome': NOMES_MESES[lote.mes_referencia - 1],
    }
    return render(request, 'leitor_fatura/preview.html', contexto)


def confirmar(request, lote_id):
    lote = get_object_or_404(ImportacaoLote, pk=lote_id, status=ImportacaoLote.Status.PENDENTE)
    if request.method != 'POST':
        return redirect('leitor_fatura:preview', lote_id=lote.id)

    selecionados_ids = {int(valor) for valor in request.POST.getlist('selecionado')}
    categorias_por_item = {}
    for item in lote.lancamentos.all():
        valor_categoria = request.POST.get(f'categoria_{item.id}')
        if valor_categoria:
            categorias_por_item[item.id] = int(valor_categoria)

    ImportacaoService.atualizar_selecao(lote, selecionados_ids, categorias_por_item)
    resultado = ImportacaoService.confirmar(lote)

    messages.success(
        request,
        f'{resultado["criados"]} lançamento(s) importado(s). '
        f'{resultado["ignorados"]} ignorado(s) (não selecionado(s) ou duplicado(s)).',
    )
    return redirect('transacoes:lista')


def cancelar(request, lote_id):
    lote = get_object_or_404(ImportacaoLote, pk=lote_id, status=ImportacaoLote.Status.PENDENTE)
    if request.method == 'POST':
        ImportacaoService.cancelar(lote)
        messages.info(request, 'Importação cancelada.')
        return redirect('leitor_fatura:upload')
    return redirect('leitor_fatura:preview', lote_id=lote.id)


def lista_faturas(request):
    lotes = (
        ImportacaoLote.objects.exclude(status=ImportacaoLote.Status.CANCELADO)
        .annotate(total_lancamentos=Count('lancamentos'))
        .order_by('-status', '-ano_referencia', '-mes_referencia', '-criado_em')
    )
    for lote in lotes:
        lote.mes_referencia_nome = NOMES_MESES[lote.mes_referencia - 1]
    return render(request, 'leitor_fatura/faturas_lista.html', {'lotes': lotes})


def excluir_fatura(request, lote_id):
    lote = get_object_or_404(ImportacaoLote, pk=lote_id, status=ImportacaoLote.Status.CONFIRMADO)
    if request.method == 'POST':
        quantidade = ImportacaoService.excluir_fatura(lote)
        messages.success(request, f'Fatura excluída: {quantidade} lançamento(s) removido(s).')
        return redirect('leitor_fatura:lista_faturas')
    contexto = {
        'lote': lote,
        'mes_referencia_nome': NOMES_MESES[lote.mes_referencia - 1],
        'total_lancamentos': lote.lancamentos.count(),
    }
    return render(request, 'leitor_fatura/fatura_confirmar_exclusao.html', contexto)
