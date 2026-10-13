from django import forms

from .models import Transacao


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = [
            'descricao', 'valor', 'tipo', 'categoria', 'data',
            'banco', 'natureza', 'parcela_atual', 'parcela_total', 'valor_total',
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'descricao': 'Descrição',
            'valor': 'Valor',
            'tipo': 'Tipo',
            'categoria': 'Categoria',
            'data': 'Data da compra',
            'banco': 'Banco',
            'natureza': 'Natureza do gasto',
            'parcela_atual': 'Parcela atual',
            'parcela_total': 'Total de parcelas',
            'valor_total': 'Valor total da compra',
        }
        help_texts = {
            'banco': 'Deixe em branco (lançamento manual) se não veio de uma importação.',
            'parcela_atual': 'Opcional — só para compras parceladas.',
            'parcela_total': 'Opcional — só para compras parceladas.',
            'valor_total': 'Opcional — valor total da compra, se parcelada.',
        }
