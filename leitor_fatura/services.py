import hashlib
from datetime import date

from django.db import transaction
from django.db.models import Q

from categoria.models import RegraCategorizacao
from transacoes.models import Transacao

from .models import ImportacaoLote, LancamentoImportado
from .parsers import detectar_leitor


class FormatoNaoReconhecido(Exception):
    pass


def _calcular_hash(banco: str, lancamento) -> str:
    # Inclui o tipo pra não confundir uma despesa com o estorno dela: podem cair no
    # mesmo dia, mesma descrição e mesmo valor (em módulo), só o sinal muda.
    chave = '|'.join([
        banco,
        lancamento.tipo,
        lancamento.data.isoformat(),
        lancamento.descricao.strip().lower(),
        str(lancamento.valor),
        str(lancamento.parcela_atual or ''),
    ])
    return hashlib.sha256(chave.encode('utf-8')).hexdigest()


def _sugerir_categoria(banco: str, lancamento):
    texto = f'{lancamento.descricao} {lancamento.categoria_crua}'.lower()
    regras = (
        RegraCategorizacao.objects.filter(ativo=True)
        .filter(Q(banco='') | Q(banco=banco))
        .select_related('categoria')
        .order_by('-prioridade', 'padrao')
    )
    for regra in regras:
        if regra.padrao.lower() in texto:
            return regra.categoria
    return None


def _e_pagamento_de_fatura(lancamento) -> bool:
    return lancamento.tipo == Transacao.Tipo.RECEITA and 'pagamento' in lancamento.descricao.lower()


def _checar_duplicidade_por_valor(lancamento, mes_referencia: int, ano_referencia: int):
    """Já existe alguma Transacao (manual ou de outra importação) com o mesmo valor
    nesse mês de referência? Não decide sozinho, só avisa pra pessoa escolher."""
    conflitos = Transacao.objects.filter(
        mes_referencia=mes_referencia, ano_referencia=ano_referencia,
        tipo=lancamento.tipo, valor=lancamento.valor,
    )
    if not conflitos.exists():
        return False, ''

    descricoes = [f'{t.descricao} ({t.data.strftime("%d/%m")})' for t in conflitos[:3]]
    return True, 'Já existe: ' + ', '.join(descricoes)


class ImportacaoService:
    @staticmethod
    def processar(arquivo_upload) -> ImportacaoLote:
        """Lê o arquivo enviado, detecta o banco pelo cabeçalho, faz o parse e
        guarda o resultado como um lote pendente de confirmação."""
        conteudo = arquivo_upload.read().decode('utf-8-sig')
        primeira_linha = conteudo.splitlines()[0] if conteudo.splitlines() else ''

        leitor_cls = detectar_leitor(primeira_linha)
        if leitor_cls is None:
            raise FormatoNaoReconhecido(
                'Não reconheci o formato desse arquivo. Bancos suportados hoje: Nubank, C6 Bank, XP.'
            )

        lancamentos_brutos = leitor_cls().ler(conteudo)

        # Mês de referência da fatura inteira = mês em que ela foi importada, não a
        # data de cada compra (uma compra de agosto pode ser cobrada numa fatura
        # importada em outubro, e é em outubro que ela deve contar no dashboard).
        hoje = date.today()

        lote = ImportacaoLote.objects.create(
            arquivo_nome=getattr(arquivo_upload, 'name', 'arquivo.csv'),
            banco=leitor_cls.banco,
            mes_referencia=hoje.month,
            ano_referencia=hoje.year,
        )

        itens = []
        for lancamento in lancamentos_brutos:
            hash_importacao = _calcular_hash(leitor_cls.banco, lancamento)
            duplicado = Transacao.objects.filter(hash_importacao=hash_importacao).exists()
            duplicado_valor, duplicado_valor_descricao = _checar_duplicidade_por_valor(
                lancamento, lote.mes_referencia, lote.ano_referencia,
            )
            categoria_sugerida = _sugerir_categoria(leitor_cls.banco, lancamento)
            selecionado = not duplicado and not _e_pagamento_de_fatura(lancamento)

            itens.append(LancamentoImportado(
                lote=lote,
                data=lancamento.data,
                descricao=lancamento.descricao,
                valor=lancamento.valor,
                tipo=lancamento.tipo,
                parcela_atual=lancamento.parcela_atual,
                parcela_total=lancamento.parcela_total,
                valor_total=lancamento.valor_total,
                categoria_crua=lancamento.categoria_crua,
                hash_importacao=hash_importacao,
                categoria_sugerida=categoria_sugerida,
                selecionado=selecionado,
                duplicado=duplicado,
                duplicado_valor=duplicado_valor,
                duplicado_valor_descricao=duplicado_valor_descricao,
            ))
        LancamentoImportado.objects.bulk_create(itens)
        return lote

    @staticmethod
    def atualizar_selecao(lote: ImportacaoLote, selecionados_ids: set[int], categorias_por_item: dict[int, int]):
        """Aplica os ajustes feitos pelo usuário na tela de preview antes de confirmar."""
        for item in lote.lancamentos.all():
            item.selecionado = item.id in selecionados_ids
            categoria_id = categorias_por_item.get(item.id)
            item.categoria_sugerida_id = categoria_id or None
            item.save(update_fields=['selecionado', 'categoria_sugerida'])

    @staticmethod
    @transaction.atomic
    def confirmar(lote: ImportacaoLote) -> dict:
        criados = 0
        ignorados = 0
        for item in lote.lancamentos.filter(selecionado=True, transacao__isnull=True):
            transacao = Transacao.objects.create(
                descricao=item.descricao,
                valor=item.valor,
                tipo=item.tipo,
                categoria=item.categoria_sugerida,
                data=item.data,
                mes_referencia=lote.mes_referencia,
                ano_referencia=lote.ano_referencia,
                banco=lote.banco,
                parcela_atual=item.parcela_atual,
                parcela_total=item.parcela_total,
                valor_total=item.valor_total,
                hash_importacao=item.hash_importacao,
            )
            item.transacao = transacao
            item.save(update_fields=['transacao'])
            criados += 1

        ignorados = lote.lancamentos.filter(selecionado=False).count()
        lote.status = ImportacaoLote.Status.CONFIRMADO
        lote.save(update_fields=['status'])
        return {'criados': criados, 'ignorados': ignorados}

    @staticmethod
    def cancelar(lote: ImportacaoLote) -> None:
        lote.delete()

    @staticmethod
    @transaction.atomic
    def excluir_fatura(lote: ImportacaoLote) -> int:
        """Apaga a fatura confirmada inteira: todas as Transacao criadas por ela e o
        próprio lote (os LancamentoImportado somem junto, via cascade)."""
        transacoes = Transacao.objects.filter(origem_importacao__lote=lote)
        quantidade = transacoes.count()
        transacoes.delete()
        lote.delete()
        return quantidade
