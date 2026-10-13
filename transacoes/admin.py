from django.contrib import admin

from .models import Transacao


@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor', 'tipo', 'categoria', 'banco', 'natureza', 'data')
    list_filter = ('tipo', 'categoria', 'banco', 'natureza')
    search_fields = ('descricao',)
