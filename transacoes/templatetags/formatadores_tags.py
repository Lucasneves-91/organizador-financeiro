from django import template

from ..helpers.formatadores import formatar_valor_monetario

register = template.Library()


@register.filter
def moeda(valor):
    if valor is None:
        return ''
    return formatar_valor_monetario(valor)
