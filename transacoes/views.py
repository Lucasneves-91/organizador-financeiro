from datetime import date

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render

from categoria.models import Categoria

from .forms import TransacaoForm
from .helpers.formatadores import formatar_valor_monetario
from .models import Transacao
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


def lista(request):
    mes_param = request.GET.get('mes')
    ano_param = request.GET.get('ano')

    if mes_param and ano_param:
        mes, ano = int(mes_param), int(ano_param)
    else:
        # Sem filtro explícito na URL: abre no mês do lançamento mais recente
        # (importar uma fatura de agosto não deve cair num dashboard vazio em outubro).
        hoje = date.today()
        mes, ano = TransacaoService.mes_ano_mais_recente() or (hoje.month, hoje.year)

    # Filtro "Receita/Despesa": por padrão mostra as duas. Afeta tanto os painéis
    # "por categoria" quanto a lista de lançamentos logo abaixo.
    mostrar_param = request.GET.getlist('mostrar')
    mostrar_atual = [v for v in mostrar_param if v in ('receita', 'despesa')] or ['receita', 'despesa']
    mostrar_receita = 'receita' in mostrar_atual
    mostrar_despesa = 'despesa' in mostrar_atual

    transacoes = TransacaoService.listar(mes=mes, ano=ano, tipos=mostrar_atual)
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

    # Gráfico Receitas x Despesas x Saldo em CSS puro (barras com altura proporcional
    # ao maior valor dos três) — sem depender de biblioteca externa.
    base_grafico = max(totais['total_receitas'], totais['total_despesas'], abs(totais['saldo']))
    if base_grafico > 0:
        grafico_pct_receitas = totais['total_receitas'] / base_grafico * 100
        grafico_pct_despesas = totais['total_despesas'] / base_grafico * 100
        grafico_pct_saldo = abs(totais['saldo']) / base_grafico * 100
    else:
        grafico_pct_receitas = grafico_pct_despesas = grafico_pct_saldo = 0

    # Formata como string com ponto decimal "na unha": passar float puro pro template
    # faz o Django localizar com vírgula (pt-br), o que quebra o `style="height: ...%"`.
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
        'categorias_disponiveis': Categoria.objects.filter(ativo=True),
        'mostrar_atual': mostrar_atual,
        'mostrar_receita': mostrar_receita,
        'mostrar_despesa': mostrar_despesa,
        'opcoes_dividido': Transacao.Dividido.choices,
        'soma_dividido': formatar_valor_monetario(TransacaoService.soma_dividido(transacoes)),
    }
    return render(request, 'transacoes/lista.html', contexto)


def _percentual(parte, total):
    if not total:
        return None
    return round(parte / total * 100)


def _montar_dados_mes(numero_mes: int, ano: int) -> dict:
    """Métricas do comparativo (Receitas/Despesas/Saldo + Gastos por natureza +
    cenário ideal) de um único mês — usado pela página Anual e pelo relatório PDF."""
    totais = TransacaoService.obter_totais(mes=numero_mes, ano=ano)
    natureza = TransacaoService.obter_totais_por_natureza(mes=numero_mes, ano=ano)
    receitas = totais['total_receitas']

    pct_fixo = _percentual(natureza['fixo'], receitas)
    pct_variavel = _percentual(natureza['variavel'], receitas)
    pct_investimento = _percentual(natureza['investimento'], receitas)

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
    resposta['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    return resposta


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


def _redirecionar_de_volta(request):
    """Volta pra onde o usuário estava (preserva o filtro de mês/ano) depois de um
    ajuste rápido de categoria/natureza direto na tabela."""
    proximo = request.POST.get('next', '')
    if proximo.startswith('/'):
        return redirect(proximo)
    return redirect('transacoes:lista')


def atualizar_categoria(request, transacao_id):
    if request.method == 'POST':
        TransacaoService.atualizar_categoria(transacao_id, request.POST.get('categoria') or None)
    return _redirecionar_de_volta(request)


def atualizar_natureza(request, transacao_id):
    if request.method == 'POST':
        TransacaoService.atualizar_natureza(transacao_id, request.POST.get('natureza', ''))
    return _redirecionar_de_volta(request)


def atualizar_dividido(request, transacao_id):
    if request.method == 'POST':
        TransacaoService.atualizar_dividido(transacao_id, request.POST.get('dividido', ''))
    return _redirecionar_de_volta(request)
