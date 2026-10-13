from django import forms

from .models import Categoria, RegraCategorizacao


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'tipo', 'ativo']
        labels = {
            'nome': 'Nome',
            'tipo': 'Tipo',
            'ativo': 'Ativa',
        }


class RegraCategorizacaoForm(forms.ModelForm):
    class Meta:
        model = RegraCategorizacao
        fields = ['padrao', 'categoria', 'banco', 'prioridade', 'ativo']
        labels = {
            'padrao': 'Padrão de texto',
            'categoria': 'Categoria',
            'banco': 'Banco',
            'prioridade': 'Prioridade',
            'ativo': 'Ativa',
        }
