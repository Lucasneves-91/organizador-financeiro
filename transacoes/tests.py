from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from categoria.models import Categoria

from .forms import MetaAnualForm, MetasMensaisForm, TransacaoForm
from .models import MetaEconomia, MetaMensal, Transacao
from .services.meta_service import MetaService
from .services.parcela_service import ParcelaService
from .services.transacao_service import TransacaoService

VALOR = MetaEconomia.Tipo.VALOR
PERCENTUAL = MetaEconomia.Tipo.PERCENTUAL


def _lancar(valor, tipo, mes, natureza=''):
    return TransacaoService.criar(
        descricao='teste', valor=Decimal(valor), tipo=tipo,
        data=date(2026, mes, 10), natureza=natureza,
    )


def _acompanhar(ano=2026):
    return MetaService.montar_acompanhamento(
        ano, MetaService.obter_anual(ano), MetaService.obter_mensais(ano)
    )


class MetaEconomiaTests(TestCase):
    def setUp(self):
        # Janeiro: receita 5000, investiu 1200. Fevereiro: receita 4000, investiu 300.
        _lancar('5000', Transacao.Tipo.RECEITA, 1)
        _lancar('1200', Transacao.Tipo.DESPESA, 1, Transacao.Natureza.INVESTIMENTO)
        _lancar('4000', Transacao.Tipo.RECEITA, 2)
        _lancar('300', Transacao.Tipo.DESPESA, 2, Transacao.Natureza.INVESTIMENTO)
        _lancar('900', Transacao.Tipo.DESPESA, 2, Transacao.Natureza.FIXO)

    def test_meta_diferente_em_cada_mes(self):
        MetaService.salvar_mensais(2026, {1: (VALOR, Decimal('1000')), 2: (PERCENTUAL, Decimal('5'))})
        dados = _acompanhar()
        jan, fev, mar = dados['meses'][:3]

        self.assertEqual(jan['meta'], 'R$ 1.000,00')
        self.assertTrue(jan['atingiu'])
        self.assertEqual(jan['diferenca'], '+R$ 200,00')

        self.assertEqual(fev['meta'], 'R$ 200,00')  # 5% de 4000
        self.assertTrue(fev['atingiu'])
        self.assertEqual(fev['acumulado_meta'], 'R$ 1.200,00')
        self.assertEqual(fev['acumulado_guardado'], 'R$ 1.500,00')
        self.assertTrue(fev['acumulado_atingiu'])

        # Mês sem lançamentos não entra na meta nem no acumulado.
        self.assertFalse(mar['tem_dados'])
        self.assertNotIn('meta', mar)
        self.assertEqual(dados['total']['meta'], 'R$ 1.200,00')

    def test_mes_sem_meta_fica_sem_cor(self):
        MetaService.salvar_mensais(2026, {2: (VALOR, Decimal('1000'))})
        jan, fev = _acompanhar()['meses'][:2]
        self.assertNotIn('atingiu', jan)
        self.assertFalse(fev['atingiu'])
        self.assertEqual(fev['diferenca'], '-R$ 700,00')

    def test_salvar_valor_vazio_apaga_meta_do_mes(self):
        MetaService.salvar_mensais(2026, {1: (VALOR, Decimal('1000'))})
        MetaService.salvar_mensais(2026, {1: (VALOR, None)})
        self.assertFalse(MetaMensal.objects.exists())

    def test_meta_anual_valor_fixo(self):
        MetaService.salvar_anual(2026, VALOR, Decimal('6000'))
        anual = _acompanhar()['anual']
        self.assertEqual(anual['meta'], 'R$ 6.000,00')
        self.assertEqual(anual['guardado'], 'R$ 1.500,00')
        self.assertEqual(anual['falta'], 'R$ 4.500,00')
        self.assertEqual(anual['percentual'], 25)
        self.assertEqual(anual['largura_barra'], 25)
        self.assertFalse(anual['atingiu'])

    def test_meta_anual_percentual_atingida_limita_barra(self):
        MetaService.salvar_anual(2026, PERCENTUAL, Decimal('10'))
        anual = _acompanhar()['anual']
        self.assertEqual(anual['meta'], 'R$ 900,00')  # 10% de 9000
        self.assertTrue(anual['atingiu'])
        self.assertEqual(anual['percentual'], 167)
        self.assertEqual(anual['largura_barra'], 100)

    def test_sem_meta_anual(self):
        self.assertIsNone(_acompanhar()['anual'])

    def test_form_mensal_valida_cada_mes(self):
        def valido(**dados):
            base = {f'tipo_{m}': 'valor' for m in range(1, 13)}
            return MetasMensaisForm({**base, **dados}).is_valid()

        self.assertTrue(valido())  # nenhum mês com meta
        self.assertTrue(valido(valor_3='500', tipo_4='percentual', valor_4='20'))  # misturado
        self.assertTrue(valido(valor_5='2000'))  # R$ acima de 100 é válido
        self.assertFalse(valido(valor_5='0'))
        self.assertFalse(valido(tipo_6='percentual', valor_6='120'))

    def test_form_anual(self):
        self.assertTrue(MetaAnualForm({'tipo_anual': 'valor', 'valor_anual': ''}).is_valid())
        self.assertFalse(MetaAnualForm({'tipo_anual': 'percentual', 'valor_anual': '150'}).is_valid())

    def test_pagina_meta_salva_e_exibe(self):
        url = reverse('transacoes:meta') + '?ano=2026'
        dados = {f'tipo_{m}': 'valor' for m in range(1, 13)}
        dados.update({'valor_1': '1000', 'tipo_2': 'percentual', 'valor_2': '25', 'tipo_anual': 'valor', 'valor_anual': '6000'})
        self.assertRedirects(self.client.post(url, dados), url)

        self.assertEqual(MetaMensal.objects.filter(ano=2026).count(), 2)
        self.assertEqual(MetaMensal.objects.get(ano=2026, mes=2).tipo, PERCENTUAL)
        pagina = self.client.get(url)
        self.assertContains(pagina, 'R$ 6.000,00 no ano')
        self.assertContains(pagina, 'Faltam R$ 4.500,00')
        self.assertContains(pagina, 'width: 25%')
        self.assertContains(pagina, 'class="positivo"')
        self.assertContains(pagina, 'class="negativo"')

    def test_pagina_mostra_erro_e_nao_salva(self):
        url = reverse('transacoes:meta') + '?ano=2026'
        dados = {f'tipo_{m}': 'valor' for m in range(1, 13)}
        dados.update({'valor_1': '-5', 'tipo_anual': 'valor', 'valor_anual': ''})
        resposta = self.client.post(url, dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'campo-com-erro')
        self.assertFalse(MetaMensal.objects.exists())

    def test_botao_meta_na_lista(self):
        self.assertContains(self.client.get(reverse('transacoes:lista')), reverse('transacoes:meta'))


class TipoInvestimentoTests(TestCase):
    def setUp(self):
        _lancar('5000', Transacao.Tipo.RECEITA, 3)
        _lancar('1000', Transacao.Tipo.DESPESA, 3, Transacao.Natureza.FIXO)
        self.investimento = TransacaoService.criar(
            descricao='Aporte', valor=Decimal('800'), tipo=Transacao.Tipo.INVESTIMENTO,
            data=date(2026, 3, 5), natureza=Transacao.Natureza.FIXO,
            banco=Transacao.Banco.XP_INVESTIMENTO,
        )

    def _form(self, **dados):
        base = {
            'descricao': 'Aporte', 'valor': '500', 'tipo': 'investimento',
            'data': '2026-03-10', 'banco': 'mercado_livre', 'natureza': 'variavel',
        }
        return TransacaoForm({**base, **dados})

    def test_investimento_soma_nas_despesas(self):
        totais = TransacaoService.obter_totais(mes=3, ano=2026)
        self.assertEqual(totais['total_despesas'], Decimal('1800'))
        self.assertEqual(totais['saldo'], Decimal('3200'))

    def test_investimento_entra_na_natureza_investimento(self):
        natureza = TransacaoService.obter_totais_por_natureza(mes=3, ano=2026)
        self.assertEqual(natureza['investimento'], Decimal('800'))
        self.assertEqual(natureza['fixo'], Decimal('1000'))  # o aporte "fixo" não entra aqui

    def test_investimento_aparece_nas_despesas_por_categoria(self):
        nomes = [linha['categoria'] for linha in TransacaoService.obter_despesas_por_categoria(mes=3, ano=2026)]
        self.assertIn('Investimentos', nomes)

    def test_meta_conta_investimento_como_guardado(self):
        marco = MetaService.montar_acompanhamento(2026, None, {})['meses'][2]
        self.assertEqual(marco['guardado'], 'R$ 800,00')

    def test_form_investimento_valido_limpa_campos_que_nao_se_aplicam(self):
        categoria = Categoria.objects.create(nome='Mercado', tipo=Categoria.Tipo.DESPESA)
        form = self._form(categoria=categoria.id, parcela_atual='1', parcela_total='3',
                          dividido='metade', observacao='x')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['categoria'])
        self.assertIsNone(form.cleaned_data['parcela_atual'])
        self.assertEqual(form.cleaned_data['dividido'], '')
        self.assertEqual(form.cleaned_data['observacao'], '')

    def test_form_investimento_exige_banco_de_investimento(self):
        self.assertFalse(self._form(banco='c6').is_valid())
        self.assertFalse(self._form(banco='').is_valid())
        for banco in ('mercado_livre', 'xp_investimento', 'nubank'):
            self.assertTrue(self._form(banco=banco).is_valid(), banco)

    def test_bancos_de_investimento_nao_valem_para_despesa(self):
        self.assertFalse(self._form(tipo='despesa', banco='mercado_livre').is_valid())
        self.assertTrue(self._form(tipo='despesa', banco='nubank').is_valid())

    def test_service_tambem_valida_banco(self):
        with self.assertRaises(ValidationError):
            TransacaoService.criar(
                descricao='x', valor=Decimal('10'), tipo=Transacao.Tipo.INVESTIMENTO,
                data=date(2026, 3, 1), banco=Transacao.Banco.C6,
            )

    def test_cadastro_pela_pagina(self):
        resposta = self.client.post(reverse('transacoes:cadastrar'), {
            'descricao': 'Tesouro', 'valor': '300', 'tipo': 'investimento',
            'data': '2026-03-20', 'banco': 'nubank', 'natureza': 'fixo',
        })
        self.assertRedirects(resposta, reverse('transacoes:lista'))
        self.assertTrue(Transacao.objects.filter(descricao='Tesouro', tipo='investimento').exists())

    def test_lista_tem_filtro_e_sem_categoria_para_investimento(self):
        pagina = self.client.get(reverse('transacoes:lista') + '?mes=3&ano=2026')
        self.assertContains(pagina, 'value="investimento"')
        self.assertContains(pagina, 'tag investimento')
        self.assertContains(pagina, 'XP Investimento')

    def test_formulario_tem_script_de_investimento(self):
        pagina = self.client.get(reverse('transacoes:cadastrar'))
        self.assertContains(pagina, 'data-bancos-investimento="mercado_livre,xp_investimento,nubank"')
        self.assertContains(pagina, '"parcela_atual"')

    def test_natureza_vira_investimento_automaticamente(self):
        self.assertEqual(self.investimento.natureza, Transacao.Natureza.INVESTIMENTO)  # criado com 'fixo'
        form = self._form(natureza='')  # select desabilitado não envia valor
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['natureza'], Transacao.Natureza.INVESTIMENTO)

    def test_ajuste_rapido_nao_muda_natureza_de_investimento(self):
        TransacaoService.atualizar_natureza(self.investimento.id, Transacao.Natureza.VARIAVEL)
        self.investimento.refresh_from_db()
        self.assertEqual(self.investimento.natureza, Transacao.Natureza.INVESTIMENTO)


class ParcelasFuturasTests(TestCase):
    def _compra(self, atual=3, total=6, mes=10, ano=2026, **extras):
        return TransacaoService.criar(
            descricao='Geladeira', valor=Decimal('100'), tipo=Transacao.Tipo.DESPESA,
            data=date(ano, mes, 15), parcela_atual=atual, parcela_total=total, **extras,
        )

    def _parcelas(self, compra):
        return list(
            Transacao.objects.filter(grupo_parcelas=compra.grupo_parcelas)
            .order_by('parcela_atual').values_list('parcela_atual', 'mes_referencia', 'ano_referencia', 'valor')
        )

    def test_cria_parcelas_seguintes_nos_meses_certos(self):
        compra = self._compra(atual=3, total=6, mes=11)
        self.assertEqual(self._parcelas(compra), [
            (3, 11, 2026, Decimal('100')),
            (4, 12, 2026, Decimal('100')),
            (5, 1, 2027, Decimal('100')),   # vira o ano
            (6, 2, 2027, Decimal('100')),
        ])
        gerada = Transacao.objects.get(grupo_parcelas=compra.grupo_parcelas, parcela_atual=4)
        self.assertTrue(gerada.parcela_gerada)
        self.assertEqual(gerada.descricao, 'Geladeira')
        self.assertEqual(gerada.parcela_total, 6)

    def test_parcelas_futuras_copiam_a_observacao(self):
        compra = self._compra(observacao='Presente da mãe')
        self.assertEqual(
            set(Transacao.objects.filter(grupo_parcelas=compra.grupo_parcelas).values_list('observacao', flat=True)),
            {'Presente da mãe'},
        )

    def test_ultima_parcela_ou_a_vista_nao_gera_nada(self):
        self._compra(atual=6, total=6)
        TransacaoService.criar(descricao='À vista', valor=Decimal('50'), tipo='despesa', data=date(2026, 10, 1))
        self.assertEqual(Transacao.objects.count(), 2)

    def test_editar_so_esta_parcela(self):
        compra = self._compra()
        TransacaoService.editar(compra.id, descricao='Geladeira', valor=Decimal('120'), tipo='despesa',
                                data=compra.data, parcela_atual=3, parcela_total=6)
        valores = [v for *_, v in self._parcelas(compra)]
        self.assertEqual(valores, [Decimal('120'), Decimal('100'), Decimal('100'), Decimal('100')])

    def test_editar_esta_e_as_proximas(self):
        compra = self._compra()
        TransacaoService.editar(compra.id, descricao='Geladeira Nova', valor=Decimal('120'), tipo='despesa',
                                data=compra.data, parcela_atual=3, parcela_total=6, aplicar_proximas=True)
        self.assertEqual({v for *_, v in self._parcelas(compra)}, {Decimal('120')})
        self.assertEqual(
            set(Transacao.objects.filter(grupo_parcelas=compra.grupo_parcelas).values_list('descricao', flat=True)),
            {'Geladeira Nova'},
        )

    def test_editar_a_partir_do_meio_nao_mexe_nas_anteriores(self):
        compra = self._compra()
        quarta = Transacao.objects.get(grupo_parcelas=compra.grupo_parcelas, parcela_atual=4)
        TransacaoService.editar(quarta.id, descricao='Geladeira', valor=Decimal('90'), tipo='despesa',
                                data=quarta.data, parcela_atual=4, parcela_total=6, aplicar_proximas=True)
        valores = [v for *_, v in self._parcelas(compra)]
        self.assertEqual(valores, [Decimal('100'), Decimal('90'), Decimal('90'), Decimal('90')])

    def test_excluir_so_esta_ou_com_as_proximas(self):
        compra = self._compra()
        quarta = Transacao.objects.get(grupo_parcelas=compra.grupo_parcelas, parcela_atual=4)
        TransacaoService.excluir(quarta.id)
        self.assertEqual([n for n, *_ in self._parcelas(compra)], [3, 5, 6])
        TransacaoService.excluir(compra.id, com_proximas=True)
        self.assertFalse(Transacao.objects.exists())

    def test_ajuste_rapido_repassa_para_proximas(self):
        compra = self._compra()
        categoria = Categoria.objects.create(nome='Casa', tipo=Categoria.Tipo.DESPESA)
        TransacaoService.atualizar_categoria(compra.id, categoria.id, aplicar_proximas=True)
        self.assertEqual(Transacao.objects.filter(categoria=categoria).count(), 4)
        TransacaoService.atualizar_observacao(compra.id, 'só aqui')
        self.assertEqual(Transacao.objects.filter(observacao='só aqui').count(), 1)

    def test_paginas_de_editar_e_excluir_perguntam(self):
        compra = self._compra()
        self.assertContains(self.client.get(reverse('transacoes:editar', args=[compra.id])), 'Nesta e nas próximas 3 parcela(s)')
        self.assertContains(self.client.get(reverse('transacoes:excluir', args=[compra.id])), 'Esta e as próximas 3 parcela(s)')
        self.client.post(reverse('transacoes:excluir', args=[compra.id]), {'escopo': 'proximas'})
        self.assertFalse(Transacao.objects.exists())

    def test_lista_marca_linhas_com_proximas(self):
        self._compra()
        pagina = self.client.get(reverse('transacoes:lista') + '?mes=10&ano=2026')
        self.assertContains(pagina, 'data-proximas="3"')
        self.assertContains(pagina, 'enviarAjuste(this.form)')

    def test_dashboard_e_meta_ignoram_meses_so_com_parcelas_futuras(self):
        self._compra(atual=1, total=12, mes=10)
        self.assertEqual(TransacaoService.mes_ano_mais_recente(), (10, 2026))
        dezembro = MetaService.montar_acompanhamento(2026, None, {})['meses'][11]
        self.assertFalse(dezembro['tem_dados'])

    def test_gerar_para_existentes_liga_parcelas_ja_importadas(self):
        # Outubro (7/9) e novembro (8/9) já vieram da fatura, sem grupo.
        base = dict(descricao='LOJA', valor=Decimal('50'), tipo='despesa', data=date(2026, 8, 1),
                    parcela_total=9, banco='c6')
        Transacao.objects.create(parcela_atual=7, mes_referencia=10, ano_referencia=2026, hash_importacao='a', **base)
        Transacao.objects.create(parcela_atual=8, mes_referencia=11, ano_referencia=2026, hash_importacao='b', **base)
        criadas = ParcelaService.gerar_para_existentes()
        self.assertEqual(criadas, 1)  # só a 9/9 de dezembro
        self.assertEqual(Transacao.objects.values('grupo_parcelas').distinct().count(), 1)
        self.assertEqual(ParcelaService.gerar_para_existentes(), 0)  # rodar de novo não duplica


class ParcelasNaImportacaoTests(TestCase):
    def _lote(self, mes, parcela):
        from leitor_fatura.models import ImportacaoLote, LancamentoImportado
        from leitor_fatura.services import calcular_hash
        from types import SimpleNamespace

        lote = ImportacaoLote.objects.create(arquivo_nome='f.csv', banco='c6', mes_referencia=mes, ano_referencia=2026)
        bruto = SimpleNamespace(tipo='despesa', data=date(2026, 9, 3), descricao='LOJA X', valor=Decimal('80'),
                                parcela_atual=parcela)
        LancamentoImportado.objects.create(
            lote=lote, data=bruto.data, descricao=bruto.descricao, valor=bruto.valor, tipo='despesa',
            parcela_atual=parcela, parcela_total=4, hash_importacao=calcular_hash('c6', bruto), selecionado=True,
        )
        return lote

    def test_confirmar_fatura_gera_parcelas_e_proxima_fatura_nao_duplica(self):
        from leitor_fatura.services import ImportacaoService

        ImportacaoService.confirmar(self._lote(mes=10, parcela=2))
        self.assertEqual(Transacao.objects.count(), 3)  # 2/4 em out + 3/4 nov + 4/4 dez

        # Fatura de novembro traz a 3/4 de novo: o hash bate e ela não é criada outra vez.
        resultado = ImportacaoService.confirmar(self._lote(mes=11, parcela=3))
        self.assertEqual(resultado['criados'], 0)
        self.assertEqual(Transacao.objects.count(), 3)

    def test_excluir_fatura_remove_parcelas_geradas_por_ela(self):
        from leitor_fatura.services import ImportacaoService

        lote = self._lote(mes=10, parcela=2)
        ImportacaoService.confirmar(lote)
        ImportacaoService.excluir_fatura(lote)
        self.assertFalse(Transacao.objects.exists())

    def test_script_da_lista_aparece_uma_vez_e_fora_do_titulo(self):
        pagina = self.client.get(reverse('transacoes:lista')).content.decode()
        self.assertIn('<title>Dashboard · Organizador Financeiro</title>', pagina)
        self.assertEqual(pagina.count('function enviarAjuste'), 1)
