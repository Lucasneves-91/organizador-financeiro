from django.contrib import admin

from .models import MetaEconomia, MetaMensal, Transacao


@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor', 'tipo', 'categoria', 'banco', 'natureza', 'data')
    list_filter = ('tipo', 'categoria', 'banco', 'natureza')
    search_fields = ('descricao',)


@admin.register(MetaEconomia)
class MetaEconomiaAdmin(admin.ModelAdmin):
    list_display = ('ano', 'tipo_anual', 'valor_anual')


@admin.register(MetaMensal)
class MetaMensalAdmin(admin.ModelAdmin):
    list_display = ('ano', 'mes', 'tipo', 'valor')
    list_filter = ('ano',)
