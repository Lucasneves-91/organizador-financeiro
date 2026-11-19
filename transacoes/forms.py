from django import forms

from categoria.models import Categoria

from .models import Transacao


class CategoriaSelect(forms.Select):
    """Select de categoria que marca cada <option> com o tipo da categoria
    (despesa/receita/ambos) via atributo `data-tipo`, pro JS do form.html
    esconder as que não combinam com o Tipo escolhido (ver form.html)."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        instance = getattr(value, 'instance', None)
        if instance is not None:
            option['attrs']['data-tipo'] = instance.tipo
        return option


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = [
            'descricao', 'valor', 'tipo', 'categoria', 'data',
            'banco', 'natureza', 'parcela_atual', 'parcela_total', 'valor_total', 'dividido',
            'observacao',
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'observacao': forms.Textarea(attrs={'rows': 3}),
            'categoria': CategoriaSelect,
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
            'dividido': 'Dividido',
            'observacao': 'OBS',
        }
        help_texts = {
            'banco': 'Deixe em branco (lançamento manual) se não veio de uma importação.',
            'parcela_atual': 'Opcional — só para compras parceladas.',
            'parcela_total': 'Opcional — só para compras parceladas.',
            'valor_total': 'Opcional — valor total da compra, se parcelada.',
            'dividido': 'Opcional — divide o valor por 2 ou aplica 40%.',
            'observacao': 'Opcional — qualquer informação extra sobre o lançamento.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.filter(ativo=True)
