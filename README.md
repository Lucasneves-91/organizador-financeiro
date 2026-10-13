# Organizador Financeiro

Aplicação Django para cadastro e controle de transações financeiras (receitas e despesas).

## Estrutura do projeto

```
organizador-financeiro/
├── configuracao/           # configuração do projeto Django (settings, urls, wsgi)
├── transacoes/              # app principal — cadastro manual e dashboard
│   ├── models/               # entidades (Transacao)
│   ├── services/              # regras de negócio (TransacaoService)
│   ├── helpers/                # funções de apoio (validadores, formatadores)
│   ├── templates/transacoes/    # páginas HTML (inclui o base.html compartilhado)
│   ├── admin.py, forms.py, urls.py, views.py
├── categoria/                # categorias e regras de categorização automática
├── leitor_fatura/             # importação de faturas/extratos (Nubank, C6 Bank, XP)
│   └── parsers/                 # um leitor por banco (detecção + parse do CSV)
├── main.py                  # equivalente ao manage.py padrão do Django
└── .env                      # variáveis de ambiente (não versionado)
```

## Importação de faturas

Em **Importar fatura** (`/importar/`) dá pra enviar o CSV exportado pelo banco — hoje
reconheço os formatos do **Nubank** e do **C6 Bank** pelo cabeçalho do arquivo. O fluxo é:

1. Envia o arquivo → o sistema detecta o banco e faz o parse (data, descrição, valor,
   parcela, categoria crua quando o banco manda).
2. Pré-visualização: cada linha vem com a categoria sugerida (via regras cadastradas em
   **Categorias → Regras de categorização**), uma caixa pra incluir/excluir e já vem
   desmarcado o que for pagamento de fatura (não é receita de verdade) ou já tiver sido
   importado antes (deduplicação automática).
3. Confirmar: só aí os lançamentos viram `Transacao` de verdade no banco de dados.

Lançamento manual continua funcionando normalmente em **+ Nova transação** — os campos de
banco/parcela/valor total são opcionais nesse caso.

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

- `http://127.0.0.1:8000/` — dashboard (receitas x despesas, categorias, transações do mês)
- `http://127.0.0.1:8000/nova/` — cadastrar nova transação
- `http://127.0.0.1:8000/importar/` — importar fatura (Nubank/C6)
- `http://127.0.0.1:8000/categorias/` — categorias e regras de categorização
- `http://127.0.0.1:8000/admin/` — painel administrativo do Django

## Comandos úteis

| Comando | Descrição |
|---|---|
| `python main.py runserver` | Inicia o servidor de desenvolvimento |
| `python main.py makemigrations` | Gera novas migrations a partir de mudanças nos models |
| `python main.py migrate` | Aplica as migrations pendentes no banco |
| `python main.py createsuperuser` | Cria um usuário para o Django admin |
| `python main.py shell` | Abre um shell Python com o contexto do Django carregado |
