from django import forms

from categoria.models import Categoria

from .models import MetaEconomia, Transacao
from .models.meta import TipoMeta


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

    # Campos que não se aplicam a investimento: ficam escondidos no form e são limpos ao salvar.
    CAMPOS_FORA_DO_INVESTIMENTO = ['categoria', 'parcela_atual', 'parcela_total', 'valor_total', 'dividido', 'observacao']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.filter(ativo=True)
        # Editando uma parcela que tem parcelas seguintes: pergunta onde aplicar.
        self.proximas = self.instance.proximas_parcelas().count() if self.instance.pk else 0
        if self.proximas:
            self.fields['aplicar_em'] = forms.ChoiceField(
                label='Aplicar alteração em',
                choices=[
                    ('esta', 'Só nesta parcela'),
                    ('proximas', f'Nesta e nas próximas {self.proximas} parcela(s)'),
                ],
                initial='esta',
                widget=forms.RadioSelect,
            )
        self.fields['banco'].widget.attrs.update({
            'data-bancos-investimento': ','.join(Transacao.BANCOS_INVESTIMENTO),
            'data-bancos-so-investimento': ','.join(Transacao.BANCOS_SO_INVESTIMENTO),
        })

    def aplicar_nas_proximas(self) -> bool:
        return self.cleaned_data.get('aplicar_em') == 'proximas'

    def dados_da_transacao(self) -> dict:
        dados = dict(self.cleaned_data)
        dados.pop('aplicar_em', None)
        return dados

    def clean(self):
        dados = super().clean()
        tipo = dados.get('tipo')
        banco = dados.get('banco', '')
        if tipo == Transacao.Tipo.INVESTIMENTO:
            dados['natureza'] = Transacao.Natureza.INVESTIMENTO
            for campo in self.CAMPOS_FORA_DO_INVESTIMENTO:
                dados[campo] = '' if campo in ('dividido', 'observacao') else None
            if banco not in Transacao.BANCOS_INVESTIMENTO:
                nomes = ', '.join(Transacao.Banco(b).label for b in Transacao.BANCOS_INVESTIMENTO)
                self.add_error('banco', f'Para investimento, escolha: {nomes}.')
        elif banco in Transacao.BANCOS_SO_INVESTIMENTO:
            self.add_error('banco', f'{Transacao.Banco(banco).label} só pode ser usado em investimentos.')
        return dados


def _validar_meta(form, campo_tipo, campo_valor, dados):
    valor = dados.get(campo_valor)
    if valor is None:
        return
    if valor <= 0:
        form.add_error(campo_valor, 'Informe um valor maior que zero.')
    elif dados.get(campo_tipo) == TipoMeta.PERCENTUAL and valor > 100:
        form.add_error(campo_valor, 'A porcentagem não pode passar de 100%.')


class MetaAnualForm(forms.ModelForm):
    class Meta:
        model = MetaEconomia
        fields = ['tipo_anual', 'valor_anual']
        labels = {'tipo_anual': 'Tipo', 'valor_anual': 'Valor'}
        widgets = {
            'valor_anual': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': 'Sem meta'}),
        }

    def clean(self):
        dados = super().clean()
        _validar_meta(self, 'tipo_anual', 'valor_anual', dados)
        return dados


class MetasMensaisForm(forms.Form):
    """Um par tipo/valor por mês (tipo_1, valor_1 ... tipo_12, valor_12).
    Valor em branco = mês sem meta."""

    def __init__(self, *args, metas=None, **kwargs):
        super().__init__(*args, **kwargs)
        metas = metas or {}
        for mes in range(1, 13):
            meta = metas.get(mes)
            self.fields[f'tipo_{mes}'] = forms.ChoiceField(
                choices=TipoMeta.choices, initial=meta.tipo if meta else TipoMeta.VALOR,
            )
            self.fields[f'valor_{mes}'] = forms.DecimalField(
                max_digits=10, decimal_places=2, required=False,
                initial=meta.valor if meta else None,
                widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '-'}),
            )

    def clean(self):
        dados = super().clean()
        for mes in range(1, 13):
            _validar_meta(self, f'tipo_{mes}', f'valor_{mes}', dados)
        return dados

    def campos_do_mes(self, mes: int):
        return self[f'tipo_{mes}'], self[f'valor_{mes}']

    def metas_por_mes(self) -> dict:
        return {
            mes: (self.cleaned_data[f'tipo_{mes}'], self.cleaned_data[f'valor_{mes}'])
            for mes in range(1, 13)
        }
