from django.contrib import admin

from .models import Categoria, RegraCategorizacao


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'ativo')
    list_filter = ('tipo', 'ativo')
    search_fields = ('nome',)


@admin.register(RegraCategorizacao)
class RegraCategorizacaoAdmin(admin.ModelAdmin):
    list_display = ('padrao', 'categoria', 'banco', 'prioridade', 'ativo')
    list_filter = ('banco', 'ativo')
    search_fields = ('padrao',)
