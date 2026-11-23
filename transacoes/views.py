import json
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from categoria.models import Categoria

from .forms import MetaAnualForm, MetasMensaisForm, TransacaoForm
from .helpers.formatadores import formatar_valor_monetario
from .models import Transacao
from .services.meta_service import MetaService
from .services.relatorio_pdf_service import RelatorioPdfService
from .services.transacao_service import TransacaoService

NOMES_MESES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

# Cenário ideal usado no comparativo anual (igual à planilha original).
LIMITE_IDEAL_FIXO = 30
LIMITE_IDEAL_VARIAVEL = 50
LIMITE_IDEAL_INVESTIMENTO = 20

CAMPOS_FORA_DO_INVESTIMENTO_JSON = json.dumps(TransacaoForm.CAMPOS_FORA_DO_INVESTIMENTO)


def lista(request):
    mes_param = request.GET.get('mes')
    ano_param = request.GET.get('ano')

    if mes_param and ano_param:
        mes, ano = int(mes_param), int(ano_param)
    else:
        # Sem filtro na URL: abre no mês mais recente com lançamentos.
        hoje = date.today()
        mes, ano = TransacaoService.mes_ano_mais_recente() or (hoje.month, hoje.year)

    # Filtro Receita/Despesa/Investimento (padrão: todos).
    mostrar_param = request.GET.getlist('mostrar')
    tipos_validos = [valor for valor, _ in Transacao.Tipo.choices]
    mostrar_atual = [v for v in mostrar_param if v in tipos_validos] or tipos_validos
    mostrar_receita = 'receita' in mostrar_atual
    mostrar_despesa = 'despesa' in mostrar_atual
    mostrar_investimento = 'investimento' in mostrar_atual

    # Filtro por banco (padrão: todos). Afeta só a lista de lançamentos.
    bancos_disponiveis = TransacaoService.bancos_disponiveis(mes=mes, ano=ano)
    bancos_validos = [valor for valor, _ in bancos_disponiveis]
    banco_param = request.GET.getlist('banco')
    bancos_atual = [v for v in banco_param if v in bancos_validos] or bancos_validos

    transacoes = TransacaoService.listar(mes=mes, ano=ano, tipos=mostrar_atual, bancos=bancos_atual)
    transacoes = TransacaoService.anotar_proximas_parcelas(transacoes)
    grupos_transacoes = TransacaoService.agrupar_por_banco(transacoes)
    totais = TransacaoService.obter_totais(mes=mes, ano=ano)
    despesas_por_categoria = TransacaoService.obter_despesas_por_categoria(mes=mes, ano=ano)
    receitas_por_categoria = TransacaoService.obter_receitas_por_categoria(mes=mes, ano=ano)

    for indice, linha in enumerate(despesas_por_categoria):
        linha['cor'] = f'cor-{indice % 8 + 1}'
        linha['total_formatado'] = formatar_valor_monetario(linha['total'])

    for indice, linha in enumerate(receitas_por_categoria):
        linha['cor'] = f'cor-{indice % 8 + 1}'
        linha['total_formatado'] = formatar_valor_monetario(linha['total'])

    anos_disponiveis = sorted(set(TransacaoService.anos_disponiveis()) | {ano}, reverse=True)

    # Filtros atuais, para os ajustes rápidos voltarem à lista sem perdê-los.
    querystring_filtros = urlencode(
        [('mes', mes), ('ano', ano)]
        + [('mostrar', valor) for valor in mostrar_atual]
        + [('banco', valor) for valor in bancos_atual]
    )

    # Gráfico em CSS puro: altura das barras proporcional ao maior dos três valores.
    base_grafico = max(totais['total_receitas'], totais['total_despesas'], abs(totais['saldo']))
    if base_grafico > 0:
        grafico_pct_receitas = totais['total_receitas'] / base_grafico * 100
        grafico_pct_despesas = totais['total_despesas'] / base_grafico * 100
        grafico_pct_saldo = abs(totais['saldo']) / base_grafico * 100
    else:
        grafico_pct_receitas = grafico_pct_despesas = grafico_pct_saldo = 0

    # Ponto decimal fixo: float no template sai com vírgula (pt-br) e quebra o CSS.
    def pct_css(valor):
        return f'{float(valor):.2f}'

    contexto = {
        'grupos_transacoes': grupos_transacoes,
        'total_receitas': formatar_valor_monetario(totais['total_receitas']),
        'total_despesas': formatar_valor_monetario(totais['total_despesas']),
        'saldo': formatar_valor_monetario(totais['saldo']),
        'saldo_positivo': totais['saldo'] >= 0,
        'percentual_receitas': totais['percentual_receitas'],
        'percentual_despesas': totais['percentual_despesas'],
        'percentual_economia': totais['percentual_economia'],
        'despesas_por_categoria': despesas_por_categoria,
        'receitas_por_categoria': receitas_por_categoria,
        'mes_selecionado': mes,
        'ano_selecionado': ano,
        'meses': list(enumerate(NOMES_MESES, start=1)),
        'anos_disponiveis': anos_disponiveis,
        'grafico_pct_receitas': pct_css(grafico_pct_receitas),
        'grafico_pct_despesas': pct_css(grafico_pct_despesas),
        'grafico_pct_saldo': pct_css(grafico_pct_saldo),
        'categorias_despesa': Categoria.objects.filter(ativo=True, tipo__in=[Categoria.Tipo.DESPESA, Categoria.Tipo.AMBOS]),
        'categorias_receita': Categoria.objects.filter(ativo=True, tipo__in=[Categoria.Tipo.RECEITA, Categoria.Tipo.AMBOS]),
        'mostrar_atual': mostrar_atual,
        'mostrar_receita': mostrar_receita,
        'mostrar_despesa': mostrar_despesa,
        'mostrar_investimento': mostrar_investimento,
        'bancos_disponiveis': bancos_disponiveis,
        'bancos_atual': bancos_atual,
        'querystring_filtros': querystring_filtros,
        'opcoes_dividido': Transacao.Dividido.choices,
        'soma_valor': formatar_valor_monetario(TransacaoService.soma_valor(transacoes)),
        'soma_dividido': formatar_valor_monetario(TransacaoService.soma_dividido(transacoes)),
    }
    return render(request, 'transacoes/lista.html', contexto)


def _percentual(parte, total):
    if not total:
        return None
    return round(parte / total * 100)


def _montar_dados_mes(numero_mes: int, ano: int) -> dict:
    """Métricas de um mês, usadas pela página Anual e pelos relatórios PDF."""
    totais = TransacaoService.obter_totais(mes=numero_mes, ano=ano)
    natureza = TransacaoService.obter_totais_por_natureza(mes=numero_mes, ano=ano)
    receitas = totais['total_receitas']

    pct_fixo = _percentual(natureza['fixo'], receitas)
    pct_variavel = _percentual(natureza['variavel'], receitas)
    pct_investimento = _percentual(natureza['investimento'], receitas)

    # Valor ideal = limite (%) aplicado sobre a receita do mês.
    valor_ideal_fixo = receitas * LIMITE_IDEAL_FIXO / 100
    valor_ideal_variavel = receitas * LIMITE_IDEAL_VARIAVEL / 100
    valor_ideal_investimento = receitas * LIMITE_IDEAL_INVESTIMENTO / 100

    return {
        'nome': NOMES_MESES[numero_mes - 1],
        'tem_dados': bool(receitas or totais['total_despesas']),
        'receitas': formatar_valor_monetario(receitas),
        'despesas': formatar_valor_monetario(totais['total_despesas']),
        'saldo': formatar_valor_monetario(totais['saldo']),
        'saldo_positivo': totais['saldo'] >= 0,
        'gastos_variaveis': formatar_valor_monetario(natureza['variavel']),
        'gastos_fixos': formatar_valor_monetario(natureza['fixo']),
        'investimentos': formatar_valor_monetario(natureza['investimento']),
        'pct_variavel': pct_variavel,
        'pct_fixo': pct_fixo,
        'pct_investimento': pct_investimento,
        'pct_fixo_ok': pct_fixo is not None and pct_fixo <= LIMITE_IDEAL_FIXO,
        'pct_investimento_ok': pct_investimento is not None and pct_investimento >= LIMITE_IDEAL_INVESTIMENTO,
        'limite_ideal_fixo': LIMITE_IDEAL_FIXO,
        'limite_ideal_variavel': LIMITE_IDEAL_VARIAVEL,
        'limite_ideal_investimento': LIMITE_IDEAL_INVESTIMENTO,
        'valor_ideal_fixo': formatar_valor_monetario(valor_ideal_fixo),
        'valor_ideal_variavel': formatar_valor_monetario(valor_ideal_variavel),
        'valor_ideal_investimento': formatar_valor_monetario(valor_ideal_investimento),
    }


def anual(request):
    ano_param = request.GET.get('ano')
    if ano_param:
        ano = int(ano_param)
    else:
        recente = TransacaoService.mes_ano_mais_recente()
        ano = recente[1] if recente else date.today().year

    anos_disponiveis = sorted(set(TransacaoService.anos_disponiveis()) | {ano}, reverse=True)
    meses_dados = [_montar_dados_mes(numero, ano) for numero in range(1, 13)]

    contexto = {
        'meses_dados': meses_dados,
        'ano_selecionado': ano,
        'anos_disponiveis': anos_disponiveis,
        'limite_ideal_fixo': LIMITE_IDEAL_FIXO,
        'limite_ideal_variavel': LIMITE_IDEAL_VARIAVEL,
        'limite_ideal_investimento': LIMITE_IDEAL_INVESTIMENTO,
    }
    return render(request, 'transacoes/anual.html', contexto)


def meta(request):
    ano_param = request.GET.get('ano')
    if ano_param:
        ano = int(ano_param)
    else:
        recente = TransacaoService.mes_ano_mais_recente()
        ano = recente[1] if recente else date.today().year

    meta_anual = MetaService.obter_anual(ano)
    metas_mensais = MetaService.obter_mensais(ano)

    if request.method == 'POST':
        form_anual = MetaAnualForm(request.POST, instance=meta_anual)
        form_mensal = MetasMensaisForm(request.POST, metas=metas_mensais)
        if form_anual.is_valid() and form_mensal.is_valid():
            MetaService.salvar_anual(ano, **form_anual.cleaned_data)
            MetaService.salvar_mensais(ano, form_mensal.metas_por_mes())
            messages.success(request, f'Metas de {ano} salvas.')
            return redirect(f"{reverse('transacoes:meta')}?ano={ano}")
    else:
        form_anual = MetaAnualForm(instance=meta_anual)
        form_mensal = MetasMensaisForm(metas=metas_mensais)

    acompanhamento = MetaService.montar_acompanhamento(ano, meta_anual, metas_mensais)
    for mes in acompanhamento['meses']:
        mes['campo_tipo'], mes['campo_valor'] = form_mensal.campos_do_mes(mes['numero'])

    anos_disponiveis = sorted(set(TransacaoService.anos_disponiveis()) | {ano}, reverse=True)
    contexto = {
        'form_anual': form_anual,
        'form_mensal': form_mensal,
        'meta_anual': meta_anual,
        'ano_selecionado': ano,
        'anos_disponiveis': anos_disponiveis,
        **acompanhamento,
    }
    return render(request, 'transacoes/meta.html', contexto)


def relatorio_mensal_pdf(request):
    mes_param = request.GET.get('mes')
    ano_param = request.GET.get('ano')
    if mes_param and ano_param:
        mes, ano = int(mes_param), int(ano_param)
    else:
        hoje = date.today()
        mes, ano = TransacaoService.mes_ano_mais_recente() or (hoje.month, hoje.year)

    dados = _montar_dados_mes(mes, ano)
    pdf_bytes = RelatorioPdfService.gerar_relatorio_mensal(dados['nome'], ano, dados)

    nome_arquivo = f'relatorio-{dados["nome"].lower()}-{ano}.pdf'
    resposta = HttpResponse(pdf_bytes, content_type='application/pdf')
    # inline: abre no visualizador do navegador em vez de baixar direto.
    resposta['Content-Disposition'] = f'inline; filename="{nome_arquivo}"'
    return resposta


def relatorio_anual_pdf(request):
    ano_param = request.GET.get('ano')
    if ano_param:
        ano = int(ano_param)
    else:
        recente = TransacaoService.mes_ano_mais_recente()
        ano = recente[1] if recente else date.today().year

    meses_dados = [_montar_dados_mes(numero, ano) for numero in range(1, 13)]
    pdf_bytes = RelatorioPdfService.gerar_relatorio_anual(ano, meses_dados)

    nome_arquivo = f'relatorio-anual-{ano}.pdf'
    resposta = HttpResponse(pdf_bytes, content_type='application/pdf')
    resposta['Content-Disposition'] = f'inline; filename="{nome_arquivo}"'
    return resposta


def cadastrar(request):
    if request.method == 'POST':
        form = TransacaoForm(request.POST)
        if form.is_valid():
            try:
                TransacaoService.criar(**form.dados_da_transacao())
                return redirect('transacoes:lista')
            except ValidationError as erro:
                form.add_error(None, erro)
    else:
        form = TransacaoForm()
    return render(request, 'transacoes/form.html', {'form': form, 'titulo': 'Nova transação', 'campos_fora_do_investimento': CAMPOS_FORA_DO_INVESTIMENTO_JSON})


def editar(request, transacao_id):
    transacao = TransacaoService.buscar(transacao_id)
    if request.method == 'POST':
        form = TransacaoForm(request.POST, instance=transacao)
        if form.is_valid():
            try:
                TransacaoService.editar(
                    transacao_id, aplicar_proximas=form.aplicar_nas_proximas(), **form.dados_da_transacao()
                )
                return redirect('transacoes:lista')
            except ValidationError as erro:
                form.add_error(None, erro)
    else:
        form = TransacaoForm(instance=transacao)
    return render(request, 'transacoes/form.html', {'form': form, 'titulo': 'Editar transação', 'campos_fora_do_investimento': CAMPOS_FORA_DO_INVESTIMENTO_JSON})


def excluir(request, transacao_id):
    transacao = TransacaoService.buscar(transacao_id)
    if request.method == 'POST':
        TransacaoService.excluir(transacao_id, com_proximas=request.POST.get('escopo') == 'proximas')
        return redirect('transacoes:lista')
    contexto = {'transacao': transacao, 'proximas': transacao.proximas_parcelas().count()}
    return render(request, 'transacoes/confirmar_exclusao.html', contexto)


def _aplicar_proximas(request) -> bool:
    return request.POST.get('aplicar_proximas') == '1'


def _redirecionar_de_volta(request):
    """Volta para a lista com os filtros que estavam aplicados."""
    proximo = request.POST.get('next', '')
    if proximo.startswith('/'):
        return redirect(proximo)
    return redirect('transacoes:lista')


def atualizar_categoria(request, transacao_id):
    if request.method == 'POST':
        TransacaoService.atualizar_categoria(transacao_id, request.POST.get('categoria') or None, aplicar_proximas=_aplicar_proximas(request))
    return _redirecionar_de_volta(request)


def atualizar_natureza(request, transacao_id):
    if request.method == 'POST':
        TransacaoService.atualizar_natureza(transacao_id, request.POST.get('natureza', ''), aplicar_proximas=_aplicar_proximas(request))
    return _redirecionar_de_volta(request)


def atualizar_dividido(request, transacao_id):
    if request.method == 'POST':
        TransacaoService.atualizar_dividido(transacao_id, request.POST.get('dividido', ''), aplicar_proximas=_aplicar_proximas(request))
    return _redirecionar_de_volta(request)


def atualizar_valor_dividido(request, transacao_id):
    if request.method == 'POST':
        bruto = request.POST.get('valor_dividido', '').strip()
        try:
            valor_dividido = Decimal(bruto) if bruto else None
        except InvalidOperation:
            valor_dividido = None
        TransacaoService.atualizar_valor_dividido(transacao_id, valor_dividido, aplicar_proximas=_aplicar_proximas(request))
    return _redirecionar_de_volta(request)


def atualizar_observacao(request, transacao_id):
    if request.method == 'POST':
        TransacaoService.atualizar_observacao(transacao_id, request.POST.get('observacao', ''), aplicar_proximas=_aplicar_proximas(request))
    return _redirecionar_de_volta(request)
