"""
Configuração WSGI do projeto configuracao.

Expõe o callable WSGI como uma variável de módulo chamada ``application``.

Para mais informações sobre este arquivo, veja
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuracao.settings')

application = get_wsgi_application()
