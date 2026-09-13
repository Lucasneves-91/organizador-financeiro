from django import forms

from .models import Transacao


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ['descricao', 'valor', 'tipo', 'categoria', 'data']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'descricao': 'Descrição',
            'valor': 'Valor',
            'tipo': 'Tipo',
            'categoria': 'Categoria',
            'data': 'Data',
        }
