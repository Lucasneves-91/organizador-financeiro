from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404

from ..helpers.validadores import validar_banco_do_tipo, validar_tipo, validar_valor_positivo
from ..models import Transacao
from .parcela_service import ParcelaService


class TransacaoService:
    @staticmethod
    def _filtrar_por_periodo(queryset, mes=None, ano=None):
        # Filtra pelo mês de referência (competência), não pela data da compra —
        # uma fatura importada em outubro conta em outubro, mesmo com compras de agosto.
        if ano:
            queryset = queryset.filter(ano_referencia=ano)
        if mes:
            queryset = queryset.filter(mes_referencia=mes)
        return queryset

    @staticmethod
    def listar(mes=None, ano=None, tipos=None, bancos=None):
        queryset = Transacao.objects.select_related('categoria').all()
        queryset = TransacaoService._filtrar_por_periodo(queryset, mes, ano)
        if tipos:
            queryset = queryset.filter(tipo__in=tipos)
        if bancos:
            valores = set(bancos)
            if Transacao.Banco.MANUAL in valores:
                # Lançamento manual não grava 'manual' no banco, fica em branco.
                valores.add('')
            queryset = queryset.filter(banco__in=valores)
        return queryset

    @staticmethod
    def bancos_disponiveis(mes=None, ano=None) -> list:
        """Bancos com lançamento no período (não é uma lista fixa)."""
        rotulos = dict(Transacao.Banco.choices)
        ordem_bancos = [valor for valor, _ in Transacao.Banco.choices]

        base = TransacaoService._filtrar_por_periodo(Transacao.objects.all(), mes, ano)
        valores_existentes = set(base.exclude(banco='').values_list('banco', flat=True).distinct())
        if base.filter(banco='').exists():
            valores_existentes.add(Transacao.Banco.MANUAL)

        ordenados = [valor for valor in ordem_bancos if valor in valores_existentes]
        extras = sorted(valores_existentes - set(ordem_bancos))
        return [(valor, rotulos.get(valor, valor.capitalize())) for valor in ordenados + extras]

    @staticmethod
    def anotar_proximas_parcelas(transacoes) -> list:
        """Preenche `qtd_proximas` (quantas parcelas da mesma compra vêm depois) em cada item."""
        transacoes = list(transacoes)
        grupos = {t.grupo_parcelas for t in transacoes if t.grupo_parcelas}
        parcelas_por_grupo = {}
        for grupo, numero in Transacao.objects.filter(grupo_parcelas__in=grupos).values_list(
            'grupo_parcelas', 'parcela_atual'
        ):
            parcelas_por_grupo.setdefault(grupo, []).append(numero or 0)
        for t in transacoes:
            numeros = parcelas_por_grupo.get(t.grupo_parcelas, [])
            t.qtd_proximas = sum(1 for n in numeros if n > (t.parcela_atual or 0))
        return transacoes

    @staticmethod
    def agrupar_por_banco(transacoes) -> list:
        """Agrupa os lançamentos por banco, na ordem de Transacao.Banco."""
        rotulos = dict(Transacao.Banco.choices)
        ordem_bancos = [valor for valor, _ in Transacao.Banco.choices]

        baldes = {valor: [] for valor in ordem_bancos}
        for transacao in transacoes:
            chave = transacao.banco or Transacao.Banco.MANUAL
            baldes.setdefault(chave, []).append(transacao)

        return [
            {'banco': rotulos.get(valor, valor), 'itens': baldes[valor]}
            for valor in ordem_bancos
            if baldes[valor]
        ]

    @staticmethod
    def obter_totais_por_natureza(mes=None, ano=None) -> dict:
        """Soma das saídas do período por natureza (fixo/variável/investimento).
        Todo lançamento do Tipo Investimento entra em 'investimento', qualquer que
        seja a natureza escolhida nele."""
        base = TransacaoService._filtrar_por_periodo(Transacao.objects.all(), mes, ano)
        totais = {valor: Decimal('0') for valor, _ in Transacao.Natureza.choices}
        despesas = base.filter(tipo=Transacao.Tipo.DESPESA)
        for item in despesas.values('natureza').annotate(total=Sum('valor')):
            if item['natureza'] in totais:
                totais[item['natureza']] = item['total']
        investimentos = base.filter(tipo=Transacao.Tipo.INVESTIMENTO).aggregate(soma=Sum('valor'))['soma']
        totais[Transacao.Natureza.INVESTIMENTO] += investimentos or Decimal('0')
        return totais

    @staticmethod
    def soma_dividido(transacoes) -> Decimal:
        return sum(
            (transacao.valor_dividido for transacao in transacoes if transacao.valor_dividido is not None),
            Decimal('0'),
        )

    @staticmethod
    def soma_valor(transacoes) -> Decimal:
        return sum((transacao.valor for transacao in transacoes), Decimal('0'))

    @staticmethod
    def obter_totais(mes=None, ano=None) -> dict:
        base = TransacaoService._filtrar_por_periodo(Transacao.objects.all(), mes, ano)

        total_receitas = base.filter(tipo=Transacao.Tipo.RECEITA).aggregate(
            soma=Sum('valor')
        )['soma'] or Decimal('0')
        total_despesas = base.filter(tipo__in=Transacao.TIPOS_SAIDA).aggregate(
            soma=Sum('valor')
        )['soma'] or Decimal('0')

        total_movimentado = total_receitas + total_despesas
        if total_movimentado > 0:
            percentual_receitas = round(total_receitas / total_movimentado * 100)
            percentual_despesas = round(total_despesas / total_movimentado * 100)
        else:
            percentual_receitas = 0
            percentual_despesas = 0

        saldo = total_receitas - total_despesas
        if total_receitas > 0:
            percentual_economia = max(0, min(100, round(saldo / total_receitas * 100)))
        else:
            percentual_economia = 0

        return {
            'total_receitas': total_receitas,
            'total_despesas': total_despesas,
            'saldo': saldo,
            'percentual_receitas': percentual_receitas,
            'percentual_despesas': percentual_despesas,
            'percentual_economia': percentual_economia,
        }

    @staticmethod
    def _agrupar_por_categoria(tipo: str, limite: int, mes=None, ano=None) -> list:
        base = TransacaoService._filtrar_por_periodo(Transacao.objects.all(), mes, ano)

        itens = list(
            base.filter(tipo=tipo)
            .values('categoria__nome')
            .annotate(total=Sum('valor'))
        )
        if tipo == Transacao.Tipo.DESPESA:
            # Investimentos não têm categoria: entram num grupo próprio.
            investido = base.filter(tipo=Transacao.Tipo.INVESTIMENTO).aggregate(soma=Sum('valor'))['soma']
            if investido:
                itens.append({'categoria__nome': 'Investimentos', 'total': investido})
        itens.sort(key=lambda item: item['total'], reverse=True)

        total_geral = sum((item['total'] for item in itens), Decimal('0'))
        if total_geral == 0:
            return []

        linhas = []
        for item in itens[:limite]:
            linhas.append({
                'categoria': item['categoria__nome'] or 'Sem categoria',
                'total': item['total'],
                'percentual': round(item['total'] / total_geral * 100),
            })

        restante = itens[limite:]
        if restante:
            total_outras = sum((item['total'] for item in restante), Decimal('0'))
            linhas.append({
                'categoria': 'Outras categorias',
                'total': total_outras,
                'percentual': round(total_outras / total_geral * 100),
            })

        return linhas

    @staticmethod
    def obter_despesas_por_categoria(limite: int = 6, mes=None, ano=None) -> list:
        return TransacaoService._agrupar_por_categoria(Transacao.Tipo.DESPESA, limite, mes, ano)

    @staticmethod
    def obter_receitas_por_categoria(limite: int = 6, mes=None, ano=None) -> list:
        return TransacaoService._agrupar_por_categoria(Transacao.Tipo.RECEITA, limite, mes, ano)

    @staticmethod
    def mes_tem_lancamentos(mes: int, ano: int) -> bool:
        """Há algum lançamento real no mês (ignora parcelas futuras geradas)?"""
        return Transacao.objects.filter(
            mes_referencia=mes, ano_referencia=ano, parcela_gerada=False
        ).exists()

    @staticmethod
    def mes_ano_mais_recente():
        """Mês/ano de referência mais recente com lançamentos, ou None se não houver nenhum."""
        ultima = (
            Transacao.objects.filter(parcela_gerada=False)
            .order_by('-ano_referencia', '-mes_referencia', '-data').first()
        )
        return (ultima.mes_referencia, ultima.ano_referencia) if ultima else None

    @staticmethod
    def anos_disponiveis() -> list:
        return list(
            Transacao.objects.order_by('-ano_referencia')
            .values_list('ano_referencia', flat=True)
            .distinct()
        )

    @staticmethod
    def buscar(transacao_id: int) -> Transacao:
        return get_object_or_404(Transacao, pk=transacao_id)

    @staticmethod
    def criar(descricao: str, valor, tipo: str, data, categoria=None, **extras) -> Transacao:
        validar_valor_positivo(valor)
        validar_tipo(tipo)
        validar_banco_do_tipo(tipo, extras.get('banco', ''))
        if tipo == Transacao.Tipo.INVESTIMENTO:
            extras['natureza'] = Transacao.Natureza.INVESTIMENTO

        # Lançamento manual: mês de referência = mês da própria data, a não ser que
        # já tenha vindo explícito (caso da importação, que define o seu próprio mês).
        extras.setdefault('mes_referencia', data.month)
        extras.setdefault('ano_referencia', data.year)

        transacao = Transacao(
            descricao=descricao,
            valor=valor,
            tipo=tipo,
            categoria=categoria,
            data=data,
            **extras,
        )
        transacao.full_clean()
        transacao.save()
        ParcelaService.gerar_futuras(transacao)
        return transacao

    @staticmethod
    def editar(transacao_id: int, descricao: str, valor, tipo: str, data, categoria=None,
               aplicar_proximas: bool = False, **extras) -> Transacao:
        validar_valor_positivo(valor)
        validar_tipo(tipo)
        validar_banco_do_tipo(tipo, extras.get('banco', ''))
        if tipo == Transacao.Tipo.INVESTIMENTO:
            extras['natureza'] = Transacao.Natureza.INVESTIMENTO

        transacao = TransacaoService.buscar(transacao_id)

        # Se for um lançamento manual (não veio de importação), editar a data também
        # realinha o mês de referência. Lançamento importado preserva a competência
        # original da fatura mesmo que a data da compra seja ajustada depois.
        if not transacao.hash_importacao:
            extras.setdefault('mes_referencia', data.month)
            extras.setdefault('ano_referencia', data.year)

        transacao.descricao = descricao
        transacao.valor = valor
        transacao.tipo = tipo
        transacao.categoria = categoria
        transacao.data = data
        for campo, valor_extra in extras.items():
            setattr(transacao, campo, valor_extra)
        transacao.full_clean()
        transacao.save()
        if aplicar_proximas:
            ParcelaService.aplicar_nas_proximas(transacao)
        ParcelaService.gerar_futuras(transacao)
        return transacao

    @staticmethod
    def excluir(transacao_id: int, com_proximas: bool = False) -> None:
        transacao = TransacaoService.buscar(transacao_id)
        if com_proximas:
            ParcelaService.excluir_com_proximas(transacao)
        else:
            transacao.delete()

    @staticmethod
    def atualizar_categoria(transacao_id: int, categoria_id, aplicar_proximas: bool = False) -> Transacao:
        transacao = TransacaoService.buscar(transacao_id)
        transacao.categoria_id = categoria_id or None
        transacao.save(update_fields=['categoria'])
        if aplicar_proximas:
            ParcelaService.aplicar_nas_proximas(transacao, ['categoria_id'])
        return transacao

    @staticmethod
    def atualizar_natureza(transacao_id: int, natureza: str, aplicar_proximas: bool = False) -> Transacao:
        transacao = TransacaoService.buscar(transacao_id)
        if transacao.tipo == Transacao.Tipo.INVESTIMENTO:
            return transacao  # natureza de investimento é sempre "Investimento"
        transacao.natureza = natureza
        transacao.save(update_fields=['natureza'])
        if aplicar_proximas:
            ParcelaService.aplicar_nas_proximas(transacao, ['natureza'])
        return transacao

    @staticmethod
    def atualizar_dividido(transacao_id: int, dividido: str, aplicar_proximas: bool = False) -> Transacao:
        """Preenche o valor dividido com a sugestão (metade/40%), que pode ser editada depois."""
        transacao = TransacaoService.buscar(transacao_id)
        transacao.dividido = dividido
        transacao.valor_dividido = transacao.sugerir_valor_dividido()
        transacao.save(update_fields=['dividido', 'valor_dividido'])
        if aplicar_proximas:
            ParcelaService.aplicar_nas_proximas(transacao, ['dividido', 'valor_dividido'])
        return transacao

    @staticmethod
    def atualizar_valor_dividido(transacao_id: int, valor_dividido, aplicar_proximas: bool = False) -> Transacao:
        transacao = TransacaoService.buscar(transacao_id)
        transacao.valor_dividido = valor_dividido
        transacao.save(update_fields=['valor_dividido'])
        if aplicar_proximas:
            ParcelaService.aplicar_nas_proximas(transacao, ['valor_dividido'])
        return transacao

    @staticmethod
    def atualizar_observacao(transacao_id: int, observacao: str, aplicar_proximas: bool = False) -> Transacao:
        transacao = TransacaoService.buscar(transacao_id)
        transacao.observacao = observacao
        transacao.save(update_fields=['observacao'])
        if aplicar_proximas:
            ParcelaService.aplicar_nas_proximas(transacao, ['observacao'])
        return transacao
