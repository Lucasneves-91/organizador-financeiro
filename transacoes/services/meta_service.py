from decimal import Decimal

from ..helpers.formatadores import formatar_valor_monetario
from ..models import MetaEconomia, MetaMensal
from .transacao_service import TransacaoService

NOMES_MESES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


def _formatar_diferenca(valor: Decimal) -> str:
    sinal = '+' if valor >= 0 else '-'
    return f'{sinal}{formatar_valor_monetario(abs(valor))}'


class MetaService:
    @staticmethod
    def obter_anual(ano: int):
        return MetaEconomia.objects.filter(ano=ano).first()

    @staticmethod
    def obter_mensais(ano: int) -> dict:
        return {meta.mes: meta for meta in MetaMensal.objects.filter(ano=ano)}

    @staticmethod
    def salvar_anual(ano: int, tipo_anual: str, valor_anual) -> MetaEconomia:
        meta, _ = MetaEconomia.objects.update_or_create(
            ano=ano, defaults={'tipo_anual': tipo_anual, 'valor_anual': valor_anual}
        )
        return meta

    @staticmethod
    def salvar_mensais(ano: int, metas: dict) -> None:
        """`metas` = {mes: (tipo, valor)}; valor None apaga a meta daquele mês."""
        for mes, (tipo, valor) in metas.items():
            if valor is None:
                MetaMensal.objects.filter(ano=ano, mes=mes).delete()
            else:
                MetaMensal.objects.update_or_create(
                    ano=ano, mes=mes, defaults={'tipo': tipo, 'valor': valor}
                )

    @staticmethod
    def montar_acompanhamento(ano: int, meta_anual, metas_mensais: dict) -> dict:
        """Meta x guardado (investimentos) mês a mês, com acumulados e meta anual.

        Meses sem nenhum lançamento ficam de fora dos acumulados, para que os meses
        que ainda não aconteceram não contem como meta não atingida.
        """
        meses = []
        receita_ano = Decimal('0')
        acumulado_meta = Decimal('0')
        acumulado_guardado = Decimal('0')
        algum_mes_com_meta = False

        for numero in range(1, 13):
            totais = TransacaoService.obter_totais(mes=numero, ano=ano)
            receitas = totais['total_receitas']
            tem_dados = TransacaoService.mes_tem_lancamentos(numero, ano)
            guardado = TransacaoService.obter_totais_por_natureza(mes=numero, ano=ano)['investimento']
            meta_mes = metas_mensais.get(numero)

            mes = {'numero': numero, 'nome': NOMES_MESES[numero - 1], 'tem_dados': tem_dados}
            if tem_dados:
                receita_ano += receitas
                acumulado_guardado += guardado
                mes.update({
                    'receitas': formatar_valor_monetario(receitas),
                    'guardado': formatar_valor_monetario(guardado),
                    'acumulado_guardado': formatar_valor_monetario(acumulado_guardado),
                })
                if meta_mes:
                    algum_mes_com_meta = True
                    valor_meta = meta_mes.valor_do_mes(receitas)
                    acumulado_meta += valor_meta
                    mes.update({
                        'meta': formatar_valor_monetario(valor_meta),
                        'diferenca': _formatar_diferenca(guardado - valor_meta),
                        'atingiu': guardado >= valor_meta,
                    })
                if algum_mes_com_meta:
                    mes.update({
                        'acumulado_meta': formatar_valor_monetario(acumulado_meta),
                        'acumulado_atingiu': acumulado_guardado >= acumulado_meta,
                    })
            meses.append(mes)

        tem_algum_dado = any(m['tem_dados'] for m in meses)
        total = {
            'tem_dados': tem_algum_dado,
            'receitas': formatar_valor_monetario(receita_ano),
            'guardado': formatar_valor_monetario(acumulado_guardado),
        }
        if algum_mes_com_meta:
            total.update({
                'meta': formatar_valor_monetario(acumulado_meta),
                'diferenca': _formatar_diferenca(acumulado_guardado - acumulado_meta),
                'atingiu': acumulado_guardado >= acumulado_meta,
            })

        anual = None
        if meta_anual and meta_anual.tem_anual:
            valor_anual = meta_anual.valor_do_ano(receita_ano)
            percentual = round(acumulado_guardado / valor_anual * 100) if valor_anual else 0
            anual = {
                'meta': formatar_valor_monetario(valor_anual),
                'guardado': formatar_valor_monetario(acumulado_guardado),
                'diferenca': _formatar_diferenca(acumulado_guardado - valor_anual),
                'falta': formatar_valor_monetario(max(valor_anual - acumulado_guardado, Decimal('0'))),
                'atingiu': acumulado_guardado >= valor_anual,
                'percentual': percentual,
                'largura_barra': min(max(percentual, 0), 100),
            }

        return {'meses': meses, 'total': total, 'anual': anual}
