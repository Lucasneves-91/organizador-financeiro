import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BOM = colors.HexColor('#0ca30c')
CRITICO = colors.HexColor('#d03b3b')
BORDA = colors.HexColor('#e1e0d9')

ESTILO_BASE_TABELA = [
    ('FONTSIZE', (0, 0), (-1, -1), 11),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDA),
    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
]


class RelatorioPdfService:
    @staticmethod
    def gerar_relatorio_mensal(nome_mes: str, ano: int, dados: dict) -> bytes:
        """Gera o PDF do comparativo de um único mês (Receitas/Despesas/Saldo,
        Gastos por natureza e o cenário ideal) — mesmas métricas da página Anual."""
        buffer = io.BytesIO()
        documento = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
        )
        estilos = getSampleStyleSheet()
        largura_util = documento.width
        colunas = [largura_util / 2, largura_util / 2]
        elementos = []

        elementos.append(Paragraph(f'Relatório financeiro — {nome_mes}/{ano}', estilos['Title']))
        elementos.append(Spacer(1, 16))

        tabela_resumo = Table(
            [['Receitas', dados['receitas']], ['Despesas', dados['despesas']], ['Saldo', dados['saldo']]],
            colWidths=colunas,
        )
        tabela_resumo.setStyle(TableStyle(ESTILO_BASE_TABELA + [
            ('TEXTCOLOR', (1, 0), (1, 0), BOM),
            ('TEXTCOLOR', (1, 1), (1, 1), CRITICO),
            ('TEXTCOLOR', (1, 2), (1, 2), BOM if dados['saldo_positivo'] else CRITICO),
        ]))
        elementos.append(tabela_resumo)
        elementos.append(Spacer(1, 24))

        elementos.append(Paragraph('Gastos por natureza', estilos['Heading2']))
        elementos.append(Spacer(1, 8))
        tabela_natureza = Table(
            [
                ['Gastos Variáveis', dados['gastos_variaveis']],
                ['Gastos Fixo', dados['gastos_fixos']],
                ['Investimentos', dados['investimentos']],
            ],
            colWidths=colunas,
        )
        tabela_natureza.setStyle(TableStyle(ESTILO_BASE_TABELA))
        elementos.append(tabela_natureza)
        elementos.append(Spacer(1, 24))

        elementos.append(Paragraph('Cenário atual x cenário ideal', estilos['Heading2']))
        elementos.append(Spacer(1, 4))
        elementos.append(Paragraph(
            f"No máximo {dados['limite_ideal_fixo']}% de Gastos Fixos / "
            f"no máximo {dados['limite_ideal_variavel']}% de Gastos Variáveis / "
            f"no mínimo {dados['limite_ideal_investimento']}% de Investimentos "
            '(percentuais sobre as receitas do mês).',
            estilos['Normal'],
        ))
        elementos.append(Spacer(1, 8))

        def formatar_percentual(valor):
            return f'{valor}%' if valor is not None else '-'

        tabela_cenario = Table(
            [
                ['% Gastos Variáveis', formatar_percentual(dados['pct_variavel'])],
                ['% Gastos Fixos', formatar_percentual(dados['pct_fixo'])],
                ['% Investimentos', formatar_percentual(dados['pct_investimento'])],
            ],
            colWidths=colunas,
        )
        estilo_cenario = list(ESTILO_BASE_TABELA)
        if dados['pct_fixo'] is not None:
            estilo_cenario.append(('TEXTCOLOR', (1, 1), (1, 1), BOM if dados['pct_fixo_ok'] else CRITICO))
        if dados['pct_investimento'] is not None:
            estilo_cenario.append(
                ('TEXTCOLOR', (1, 2), (1, 2), BOM if dados['pct_investimento_ok'] else CRITICO)
            )
        tabela_cenario.setStyle(TableStyle(estilo_cenario))
        elementos.append(tabela_cenario)

        documento.build(elementos)
        return buffer.getvalue()
