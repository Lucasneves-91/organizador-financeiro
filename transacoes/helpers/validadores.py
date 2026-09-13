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
