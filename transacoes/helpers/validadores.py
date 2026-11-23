from decimal import Decimal

from django.core.exceptions import ValidationError


def validar_valor_positivo(valor: Decimal) -> None:
    if valor is None or valor <= 0:
        raise ValidationError('O valor deve ser maior que zero.')


def validar_tipo(tipo: str) -> None:
    from ..models import Transacao

    tipos_validos = [choice[0] for choice in Transacao.Tipo.choices]
    if tipo not in tipos_validos:
        raise ValidationError(f'Tipo inválido. Use um dos seguintes: {", ".join(tipos_validos)}.')


def validar_banco_do_tipo(tipo: str, banco: str) -> None:
    from ..models import Transacao

    if tipo == Transacao.Tipo.INVESTIMENTO:
        if banco not in Transacao.BANCOS_INVESTIMENTO:
            nomes = ', '.join(Transacao.Banco(b).label for b in Transacao.BANCOS_INVESTIMENTO)
            raise ValidationError(f'Para investimento, escolha o banco: {nomes}.')
    elif banco in Transacao.BANCOS_SO_INVESTIMENTO:
        raise ValidationError(f'{Transacao.Banco(banco).label} só pode ser usado em investimentos.')
