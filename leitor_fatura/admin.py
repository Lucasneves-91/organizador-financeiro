from django.contrib import admin

from .models import ImportacaoLote, LancamentoImportado


class LancamentoImportadoInline(admin.TabularInline):
    model = LancamentoImportado
    extra = 0
    fields = ('data', 'descricao', 'valor', 'tipo', 'categoria_sugerida', 'selecionado', 'duplicado')


@admin.register(ImportacaoLote)
class ImportacaoLoteAdmin(admin.ModelAdmin):
    list_display = ('arquivo_nome', 'banco', 'status', 'criado_em')
    list_filter = ('banco', 'status')
    inlines = [LancamentoImportadoInline]
