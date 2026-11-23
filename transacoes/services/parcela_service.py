import uuid
from types import SimpleNamespace

from django.db import transaction as db_transaction

from ..models import Transacao

# Campos que valem para a compra inteira: copiados para as parcelas futuras e
# repassados a elas quando a edição é "esta e as próximas".
CAMPOS_DA_COMPRA = [
    'descricao', 'valor', 'tipo', 'categoria_id', 'banco', 'natureza',
    'parcela_total', 'valor_total', 'dividido', 'valor_dividido', 'observacao',
]


def _somar_meses(mes: int, ano: int, quantidade: int):
    indice = (ano * 12 + mes - 1) + quantidade
    return indice % 12 + 1, indice // 12


def _hash_da_parcela(origem: Transacao, numero: int):
    """Mesmo hash que a importação calcularia para essa parcela, para a fatura do
    mês seguinte reconhecê-la como já importada."""
    if not origem.hash_importacao or not origem.banco:
        return None
    from leitor_fatura.services import calcular_hash

    lancamento = SimpleNamespace(
        tipo=origem.tipo, data=origem.data, descricao=origem.descricao,
        valor=origem.valor, parcela_atual=numero,
    )
    return calcular_hash(origem.banco, lancamento)


def buscar_parcela_existente(banco, tipo, descricao, valor, parcela_atual, parcela_total, mes, ano):
    """Lançamento que já representa essa parcela (gerado ou importado) nesse mês."""
    return Transacao.objects.filter(
        banco=banco, tipo=tipo, descricao__iexact=descricao.strip(), valor=valor,
        parcela_atual=parcela_atual, parcela_total=parcela_total,
        mes_referencia=mes, ano_referencia=ano,
    ).first()


class ParcelaService:
    @staticmethod
    def tem_parcelas(transacao: Transacao) -> bool:
        return bool(
            transacao.parcela_atual and transacao.parcela_total
            and transacao.parcela_atual < transacao.parcela_total
        )

    @staticmethod
    @db_transaction.atomic
    def gerar_futuras(origem: Transacao) -> int:
        """Cria as parcelas seguintes (parcela_atual+1 .. parcela_total), uma por mês.
        Parcelas que já existem (geradas ou importadas) só são ligadas ao grupo."""
        if not ParcelaService.tem_parcelas(origem):
            return 0

        if not origem.grupo_parcelas:
            origem.grupo_parcelas = uuid.uuid4()
            origem.save(update_fields=['grupo_parcelas'])

        criadas = 0
        for numero in range(origem.parcela_atual + 1, origem.parcela_total + 1):
            mes, ano = _somar_meses(
                origem.mes_referencia, origem.ano_referencia, numero - origem.parcela_atual
            )
            no_grupo = Transacao.objects.filter(
                grupo_parcelas=origem.grupo_parcelas, parcela_atual=numero
            ).exists()
            if no_grupo:
                continue

            existente = buscar_parcela_existente(
                origem.banco, origem.tipo, origem.descricao, origem.valor,
                numero, origem.parcela_total, mes, ano,
            )
            if existente:
                if not existente.grupo_parcelas:
                    existente.grupo_parcelas = origem.grupo_parcelas
                    existente.save(update_fields=['grupo_parcelas'])
                continue

            hash_parcela = _hash_da_parcela(origem, numero)
            if hash_parcela and Transacao.objects.filter(hash_importacao=hash_parcela).exists():
                continue

            nova = Transacao(
                data=origem.data,
                parcela_atual=numero,
                mes_referencia=mes,
                ano_referencia=ano,
                hash_importacao=hash_parcela,
                grupo_parcelas=origem.grupo_parcelas,
                parcela_gerada=True,
            )
            for campo in CAMPOS_DA_COMPRA:
                setattr(nova, campo, getattr(origem, campo))
            nova.save()
            criadas += 1
        return criadas

    @staticmethod
    @db_transaction.atomic
    def aplicar_nas_proximas(origem: Transacao, campos=None) -> int:
        """Repassa os campos da compra (ou só os indicados) para as parcelas seguintes."""
        campos = campos or CAMPOS_DA_COMPRA
        proximas = list(origem.proximas_parcelas())
        for parcela in proximas:
            for campo in campos:
                if campo == 'natureza' and parcela.tipo == Transacao.Tipo.INVESTIMENTO:
                    continue
                setattr(parcela, campo, getattr(origem, campo))
            parcela.save()

        # Se o total de parcelas diminuiu, as que sobraram saem.
        if 'parcela_total' in campos and origem.parcela_total:
            origem.proximas_parcelas().filter(parcela_atual__gt=origem.parcela_total).delete()
        return len(proximas)

    @staticmethod
    def excluir_com_proximas(origem: Transacao) -> int:
        quantidade = origem.proximas_parcelas().count()
        origem.proximas_parcelas().delete()
        origem.delete()
        return quantidade + 1

    @staticmethod
    def gerar_para_existentes() -> int:
        """Gera as parcelas futuras de todas as compras parceladas já lançadas.
        Processa da competência mais antiga para a mais nova, para que parcelas já
        importadas em meses seguintes sejam ligadas em vez de duplicadas."""
        criadas = 0
        parceladas = (
            Transacao.objects.filter(parcela_atual__isnull=False, parcela_total__isnull=False, parcela_gerada=False)
            .order_by('ano_referencia', 'mes_referencia', 'parcela_atual', 'id')
        )
        for transacao in parceladas:
            transacao.refresh_from_db()
            criadas += ParcelaService.gerar_futuras(transacao)
        return criadas
