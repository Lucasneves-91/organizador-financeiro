# Organizador Financeiro

Aplicação Django para cadastro e controle de transações financeiras (receitas e despesas).

## Estrutura do projeto

```
organizador-financeiro/
├── configuracao/           # configuração do projeto Django (settings, urls, wsgi)
├── transacoes/              # app principal
│   ├── models/               # entidades (Transacao)
│   ├── services/              # regras de negócio (TransacaoService)
│   ├── helpers/                # funções de apoio (validadores, formatadores)
│   ├── templates/transacoes/    # páginas HTML
│   ├── admin.py, forms.py, urls.py, views.py
├── main.py                  # equivalente ao manage.py padrão do Django
└── .env                      # variáveis de ambiente (não versionado)
```

## Pré-requisitos

- Python 3.11+
- MySQL rodando localmente, com o banco `organizador_financeiro` já criado

## Configuração

1. Crie e ative o ambiente virtual:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Copie o arquivo de exemplo de variáveis de ambiente e preencha com seus dados locais:

   ```bash
   cp .env.example .env
   ```

   Edite o `.env` e informe a senha do seu MySQL local em `DB_PASSWORD` (as demais variáveis já vêm com valores padrão para desenvolvimento).

4. Rode as migrations para criar as tabelas no banco:

   ```bash
   python main.py migrate
   ```

5. (Opcional) Crie um usuário admin para acessar o Django admin:

   ```bash
   python main.py createsuperuser
   ```

## Rodando o projeto

```bash
source .venv/bin/activate
python main.py runserver
```

Acesse no navegador:

- `http://127.0.0.1:8000/` — lista de transações
- `http://127.0.0.1:8000/nova/` — cadastrar nova transação
- `http://127.0.0.1:8000/admin/` — painel administrativo do Django

## Comandos úteis

| Comando | Descrição |
|---|---|
| `python main.py runserver` | Inicia o servidor de desenvolvimento |
| `python main.py makemigrations` | Gera novas migrations a partir de mudanças nos models |
| `python main.py migrate` | Aplica as migrations pendentes no banco |
| `python main.py createsuperuser` | Cria um usuário para o Django admin |
| `python main.py shell` | Abre um shell Python com o contexto do Django carregado |
