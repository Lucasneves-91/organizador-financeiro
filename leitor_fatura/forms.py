from django import forms


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
