from pathlib import Path

_CSS = Path(__file__).resolve().parent / 'static' / 'transacoes' / 'style.css'


def versao_css(request):
    """Muda a URL do CSS quando o arquivo muda, para o navegador não usar a versão em cache."""
    try:
        return {'versao_css': int(_CSS.stat().st_mtime)}
    except OSError:
        return {'versao_css': ''}
