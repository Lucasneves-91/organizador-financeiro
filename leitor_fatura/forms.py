from django import forms

from transacoes.views import NOMES_MESES


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """FileField que aceita vários arquivos de uma vez (ver docs do Django sobre
    upload de múltiplos arquivos — não existe um campo pronto pra isso)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return single_file_clean(data, initial)


class UploadFaturaForm(forms.Form):
    arquivos = MultipleFileField(label='Arquivo(s) CSV (Nubank, C6 Bank ou XP)')
    mes_referencia = forms.TypedChoiceField(
        label='Mês de referência',
        choices=[(numero, nome) for numero, nome in enumerate(NOMES_MESES, start=1)],
        coerce=int,
        help_text='Mês do dashboard em que essa fatura vai contar. Pode importar pra um mês passado.',
    )
    ano_referencia = forms.IntegerField(label='Ano de referência', min_value=2000, max_value=2100)
