from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404

from ..helpers.validadores import validar_tipo, validar_valor_positivo
from ..models import Transacao


class TransacaoService:
    @staticmethod
    def listar():
        return Transacao.objects.all()

    @staticmethod
    def obter_totais() -> dict:
        total_receitas = Transacao.objects.filter(tipo=Transacao.Tipo.RECEITA).aggregate(
            soma=Sum('valor')
        )['soma'] or Decimal('0')
        total_despesas = Transacao.objects.filter(tipo=Transacao.Tipo.DESPESA).aggregate(
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
    def obter_despesas_por_categoria(limite: int = 6) -> list:
        despesas = (
            Transacao.objects.filter(tipo=Transacao.Tipo.DESPESA)
            .values('categoria')
            .annotate(total=Sum('valor'))
            .order_by('-total')
        )

        total_despesas = sum((item['total'] for item in despesas), Decimal('0'))
        if total_despesas == 0:
            return []

        linhas = []
        for item in despesas[:limite]:
            linhas.append({
                'categoria': item['categoria'] or 'Sem categoria',
                'total': item['total'],
                'percentual': round(item['total'] / total_despesas * 100),
            })

        restante = despesas[limite:]
        if restante:
            total_outras = sum((item['total'] for item in restante), Decimal('0'))
            linhas.append({
                'categoria': 'Outras categorias',
                'total': total_outras,
                'percentual': round(total_outras / total_despesas * 100),
            })

        return linhas

    @staticmethod
    def buscar(transacao_id: int) -> Transacao:
        return get_object_or_404(Transacao, pk=transacao_id)

    @staticmethod
    def criar(descricao: str, valor, tipo: str, data, categoria: str = '') -> Transacao:
        validar_valor_positivo(valor)
        validar_tipo(tipo)

        transacao = Transacao(
            descricao=descricao,
            valor=valor,
            tipo=tipo,
            categoria=categoria,
            data=data,
        )
        transacao.full_clean()
        transacao.save()
        return transacao

    @staticmethod
    def editar(transacao_id: int, descricao: str, valor, tipo: str, data, categoria: str = '') -> Transacao:
        validar_valor_positivo(valor)
        validar_tipo(tipo)

        transacao = TransacaoService.buscar(transacao_id)
        transacao.descricao = descricao
        transacao.valor = valor
        transacao.tipo = tipo
        transacao.categoria = categoria
        transacao.data = data
        transacao.full_clean()
        transacao.save()
        return transacao

    @staticmethod
    def excluir(transacao_id: int) -> None:
        transacao = TransacaoService.buscar(transacao_id)
        transacao.delete()
