from decimal import Decimal


def formatar_valor_monetario(valor: Decimal) -> str:
    valor_formatado = f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {valor_formatado}'


def formatar_data_br(data) -> str:
    return data.strftime('%d/%m/%Y')
