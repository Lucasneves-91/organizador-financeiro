import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
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
        """PDF com as métricas de um mês."""
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

        coluna_rotulo = largura_util * 0.34
        coluna_resto = (largura_util - coluna_rotulo) / 3
        colunas_cenario = [coluna_rotulo, coluna_resto, coluna_resto, coluna_resto]

        tabela_cenario = Table(
            [
                ['', '% atual', 'Valor real', 'Valor ideal'],
                ['Gastos Variáveis', formatar_percentual(dados['pct_variavel']), dados['gastos_variaveis'], dados['valor_ideal_variavel']],
                ['Gastos Fixos', formatar_percentual(dados['pct_fixo']), dados['gastos_fixos'], dados['valor_ideal_fixo']],
                ['Investimentos', formatar_percentual(dados['pct_investimento']), dados['investimentos'], dados['valor_ideal_investimento']],
            ],
            colWidths=colunas_cenario,
        )
        estilo_cenario = list(ESTILO_BASE_TABELA) + [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BORDA),
        ]
        if dados['pct_fixo'] is not None:
            estilo_cenario.append(('TEXTCOLOR', (1, 2), (1, 2), BOM if dados['pct_fixo_ok'] else CRITICO))
        if dados['pct_investimento'] is not None:
            estilo_cenario.append(
                ('TEXTCOLOR', (1, 3), (1, 3), BOM if dados['pct_investimento_ok'] else CRITICO)
            )
        tabela_cenario.setStyle(TableStyle(estilo_cenario))
        elementos.append(tabela_cenario)

        documento.build(elementos)
        return buffer.getvalue()

    @staticmethod
    def gerar_relatorio_anual(ano: int, meses_dados: list) -> bytes:
        """PDF com a mesma grade da página Anual."""
        buffer = io.BytesIO()
        documento = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        )
        estilos = getSampleStyleSheet()
        largura_util = documento.width
        elementos = []

        elementos.append(Paragraph(f'Comparativo anual — {ano}', estilos['Title']))
        elementos.append(Spacer(1, 12))

        coluna_rotulo = largura_util * 0.14
        coluna_mes = (largura_util - coluna_rotulo) / 12
        colunas = [coluna_rotulo] + [coluna_mes] * 12

        def valor(mes, chave):
            return mes[chave] if mes['tem_dados'] else '-'

        def percentual(mes, chave):
            return f'{mes[chave]}%' if mes[chave] is not None else '-'

        linhas = [
            [''] + [mes['nome'][:3] for mes in meses_dados],
            ['Receitas'] + [valor(mes, 'receitas') for mes in meses_dados],
            ['Despesas'] + [valor(mes, 'despesas') for mes in meses_dados],
            ['Saldo'] + [valor(mes, 'saldo') for mes in meses_dados],
            ['Gastos Variáveis'] + [valor(mes, 'gastos_variaveis') for mes in meses_dados],
            ['Gastos Fixos'] + [valor(mes, 'gastos_fixos') for mes in meses_dados],
            ['Investimentos'] + [valor(mes, 'investimentos') for mes in meses_dados],
            ['% Gastos Variáveis'] + [percentual(mes, 'pct_variavel') for mes in meses_dados],
            ['% Gastos Fixos'] + [percentual(mes, 'pct_fixo') for mes in meses_dados],
            ['% Investimentos'] + [percentual(mes, 'pct_investimento') for mes in meses_dados],
        ]
        LINHA_SALDO, LINHA_PCT_FIXO, LINHA_PCT_INVESTIMENTO = 3, 8, 9

        tabela = Table(linhas, colWidths=colunas, repeatRows=1)
        estilo = [
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDA),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BORDA),
        ]
        for indice, mes in enumerate(meses_dados):
            coluna = indice + 1
            if mes['tem_dados']:
                estilo.append((
                    'TEXTCOLOR', (coluna, LINHA_SALDO), (coluna, LINHA_SALDO),
                    BOM if mes['saldo_positivo'] else CRITICO,
                ))
            if mes['pct_fixo'] is not None:
                estilo.append((
                    'TEXTCOLOR', (coluna, LINHA_PCT_FIXO), (coluna, LINHA_PCT_FIXO),
                    BOM if mes['pct_fixo_ok'] else CRITICO,
                ))
            if mes['pct_investimento'] is not None:
                estilo.append((
                    'TEXTCOLOR', (coluna, LINHA_PCT_INVESTIMENTO), (coluna, LINHA_PCT_INVESTIMENTO),
                    BOM if mes['pct_investimento_ok'] else CRITICO,
                ))
        tabela.setStyle(TableStyle(estilo))
        elementos.append(tabela)

        documento.build(elementos)
        return buffer.getvalue()
