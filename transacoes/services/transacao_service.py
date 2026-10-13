from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404

from ..helpers.validadores import validar_tipo, validar_valor_positivo
from ..models import Transacao


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
    def listar(mes=None, ano=None, tipos=None):
        queryset = Transacao.objects.select_related('categoria').all()
        queryset = TransacaoService._filtrar_por_periodo(queryset, mes, ano)
        if tipos:
            queryset = queryset.filter(tipo__in=tipos)
        return queryset

    @staticmethod
    def agrupar_por_banco(transacoes) -> list:
        """Agrupa os lançamentos já filtrados por banco (Nubank/C6/manual), na ordem
        declarada em Transacao.Banco, mantendo a ordenação original dentro de cada grupo."""
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
    def obter_totais(mes=None, ano=None) -> dict:
        base = TransacaoService._filtrar_por_periodo(Transacao.objects.all(), mes, ano)

        total_receitas = base.filter(tipo=Transacao.Tipo.RECEITA).aggregate(
            soma=Sum('valor')
        )['soma'] or Decimal('0')
        total_despesas = base.filter(tipo=Transacao.Tipo.DESPESA).aggregate(
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

        itens = (
            base.filter(tipo=tipo)
            .values('categoria__nome')
            .annotate(total=Sum('valor'))
            .order_by('-total')
        )

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
    def mes_ano_mais_recente():
        """Mês/ano de referência mais recente com lançamentos, ou None se não houver nenhum."""
        ultima = Transacao.objects.order_by('-ano_referencia', '-mes_referencia', '-data').first()
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
        return transacao

    @staticmethod
    def editar(transacao_id: int, descricao: str, valor, tipo: str, data, categoria=None, **extras) -> Transacao:
        validar_valor_positivo(valor)
        validar_tipo(tipo)

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
        return transacao

    @staticmethod
    def excluir(transacao_id: int) -> None:
        transacao = TransacaoService.buscar(transacao_id)
        transacao.delete()

    @staticmethod
    def atualizar_categoria(transacao_id: int, categoria_id) -> Transacao:
        """Ajuste rápido só da categoria, direto na listagem (sem abrir o form inteiro)."""
        transacao = TransacaoService.buscar(transacao_id)
        transacao.categoria_id = categoria_id or None
        transacao.save(update_fields=['categoria'])
        return transacao

    @staticmethod
    def atualizar_natureza(transacao_id: int, natureza: str) -> Transacao:
        """Ajuste rápido só da natureza, direto na listagem (sem abrir o form inteiro)."""
        transacao = TransacaoService.buscar(transacao_id)
        transacao.natureza = natureza
        transacao.save(update_fields=['natureza'])
        return transacao
