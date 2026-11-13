"""
Testes unitários puros para os sub-parsers e Value Objects da arquitetura refatorada.
Executam 100% em memória, com fixtures controladas e sem dependência de I/O externo.
"""

import unittest
from decimal import Decimal
from schemas import (
    IdentificacaoNFe,
    Emitente,
    Destinatario,
    TotaisImposto,
    TransporteNFe,
    NFeDocumento,
    NFeDuplicata,
    NFeItem
)
from parser_sections import (
    IdentificacaoParser,
    EmitenteParser,
    DestinatarioParser,
    TotaisImpostoParser,
    DuplicatasParser,
    TransporteParser,
    DadosAdicionaisParser,
    NFeSectionPipeline
)
from parser_items import ItemTableParser
from utils import parse_decimal, parse_date_br, clean_spaces


class TestValueObjectsAndSchemas(unittest.TestCase):
    def test_nfe_documento_flattened_dict_keys(self):
        """Garante que to_dict() retorne a estrutura plana esperada pelo exportador CSV/Excel."""
        doc = NFeDocumento(
            identificacao=IdentificacaoNFe(
                chave_acesso="12345678901234567890123456789012345678901234",
                numero_nf="100",
                serie="1",
                folha="1/1",
                tipo_operacao="1",
                natureza_operacao="VENDA",
                protocolo_autorizacao="12345"
            ),
            emitente=Emitente(
                emitente_cnpj="11.222.333/0001-44",
                emitente_ie="12345678",
                emitente_ie_st="99999",
                emitente_uf="RO"
            ),
            destinatario=Destinatario(
                destinatario_cnpj_cpf="22.333.444/0001-55",
                destinatario_ie="87654321",
                destinatario_uf="RO",
                data_emissao="2023-01-01",
                data_saida="2023-01-02",
                hora_saida="10:00:00"
            ),
            totais=TotaisImposto(
                bc_icms=Decimal("1000.00"),
                valor_icms=Decimal("180.00"),
                valor_total_nota=Decimal("1500.00")
            ),
            transporte=TransporteNFe(
                modalidade_frete="0-Emitente",
                placa_veiculo="ABC-1234"
            ),
            info_complementares="SUBST TRIBUTARIA RETIDO",
            tem_mencao_icms_st=True,
            pagina_arquivo=1,
            arquivo_origem="nota.pdf"
        )

        flat = doc.to_dict()
        self.assertIsInstance(flat, dict)

        # Valida campos-chave no dicionário plano
        expected_keys = [
            "chave_acesso", "numero_nf", "serie", "folha", "tipo_operacao", "natureza_operacao",
            "protocolo_autorizacao", "emitente_cnpj", "emitente_ie", "emitente_ie_st", "emitente_uf",
            "destinatario_cnpj_cpf", "destinatario_ie", "destinatario_uf", "data_emissao", "data_saida",
            "hora_saida", "bc_icms", "valor_icms", "bc_icms_st", "valor_icms_st", "valor_imp_importacao",
            "valor_icms_uf_remet", "valor_fcp_uf_dest", "valor_pis", "valor_total_produtos", "valor_frete",
            "valor_seguro", "valor_desconto", "outras_despesas", "valor_total_ipi", "valor_icms_uf_dest",
            "valor_tot_trib", "valor_cofins", "valor_total_nota", "modalidade_frete", "transportador_cnpj_cpf",
            "transportador_uf", "placa_veiculo", "volume_quantidade", "peso_bruto", "peso_liquido",
            "info_complementares", "tem_mencao_icms_st", "pagina_arquivo", "arquivo_origem"
        ]
        for key in expected_keys:
            self.assertIn(key, flat, f"Chave ausente no flat dict: {key}")

        # Valida propriedades de compatibilidade
        self.assertEqual(doc.chave_acesso, "12345678901234567890123456789012345678901234")
        self.assertEqual(doc.valor_total_nota, Decimal("1500.00"))
        self.assertEqual(doc.bc_icms, Decimal("1000.00"))
        self.assertEqual(doc.valor_icms, Decimal("180.00"))


class TestSubParsers(unittest.TestCase):
    def test_identificacao_parser_success(self):
        text = """
        DANFE
        1 - SAÍDA
        Nº 000.045.890
        Série 2
        Folha 1/2
        CHAVE DE ACESSO
        1234 5678 9012 3456 7890 1234 5678 9012 3456 7890 1234
        PROTOCOLO DE AUTORIZAÇÃO DE USO
        311234567890123 - 10/05/2023 14:30:00
        NATUREZA DA OPERAÇÃO
        REMESSA EM BONIFICACAO
        """
        parser = IdentificacaoParser()
        ident = parser.parse(text)
        self.assertIsNotNone(ident)
        self.assertEqual(ident.chave_acesso, "12345678901234567890123456789012345678901234")
        self.assertEqual(ident.numero_nf, "000045890")
        self.assertEqual(ident.serie, "2")
        self.assertEqual(ident.folha, "1/2")
        self.assertEqual(ident.tipo_operacao, "1")
        self.assertEqual(ident.protocolo_autorizacao, "311234567890123 - 10/05/2023 14:30:00")
        self.assertEqual(ident.natureza_operacao, "REMESSA EM BONIFICACAO")

    def test_identificacao_parser_missing_key(self):
        text = "Página sem chave de acesso válida"
        parser = IdentificacaoParser()
        self.assertIsNone(parser.parse(text))

    def test_totais_imposto_parser(self):
        lines = [
            "CÁLCULO DO IMPOSTO",
            "BASE DE CÁLCULO DO ICMS VALOR DO ICMS BASE CÁLC. ICMS S.T. VALOR DO ICMS SUBST. V. IMP. IMPORTAÇÃO V. ICMS UF REMET. V. FCP UF DEST. VALOR DO PIS VALOR TOTAL DOS PRODUTOS",
            "2.500,00 450,00 500,00 90,00 0,00 0,00 0,00 41,25 3.000,00",
            "VALOR DO FRETE VALOR DO SEGURO DESCONTO OUTRAS DESPESAS VALOR TOTAL DO IPI V. ICMS UF DEST. V. TOT. TRIB. VALOR DA COFINS VALOR TOTAL DA NOTA",
            "100,00 20,00 50,00 10,00 150,00 0,00 200,00 190,00 3.320,00"
        ]
        parser = TotaisImpostoParser()
        totais = parser.parse(lines, calc_idx=0)

        self.assertEqual(totais.bc_icms, Decimal("2500.00"))
        self.assertEqual(totais.valor_icms, Decimal("450.00"))
        self.assertEqual(totais.bc_icms_st, Decimal("500.00"))
        self.assertEqual(totais.valor_icms_st, Decimal("90.00"))
        self.assertEqual(totais.valor_pis, Decimal("41.25"))
        self.assertEqual(totais.valor_total_produtos, Decimal("3000.00"))
        self.assertEqual(totais.valor_frete, Decimal("100.00"))
        self.assertEqual(totais.valor_seguro, Decimal("20.00"))
        self.assertEqual(totais.valor_desconto, Decimal("50.00"))
        self.assertEqual(totais.outras_despesas, Decimal("10.00"))
        self.assertEqual(totais.valor_total_ipi, Decimal("150.00"))
        self.assertEqual(totais.valor_tot_trib, Decimal("200.00"))
        self.assertEqual(totais.valor_cofins, Decimal("190.00"))
        self.assertEqual(totais.valor_total_nota, Decimal("3320.00"))

    def test_duplicatas_parser_multiple(self):
        lines = [
            "FATURA / DUPLICATA",
            "Num. 1001-A Venc. 05/02/2024 Valor 1.250,50",
            "Num. 1001-B Venc. 05/03/2024 Valor 1.250,50",
            "CÁLCULO DO IMPOSTO"
        ]
        parser = DuplicatasParser()
        dups = parser.parse(
            lines=lines,
            fat_idx=0,
            calc_idx=3,
            chave_acesso="11112222333344445555666677778888999900001111",
            page_num=1
        )
        self.assertEqual(len(dups), 2)
        self.assertEqual(dups[0].numero_duplicata, "1001-A")
        self.assertEqual(dups[0].data_vencimento, "2024-02-05")
        self.assertEqual(dups[0].valor, Decimal("1250.50"))
        self.assertEqual(dups[1].numero_duplicata, "1001-B")
        self.assertEqual(dups[1].data_vencimento, "2024-03-05")
        self.assertEqual(dups[1].valor, Decimal("1250.50"))

    def test_dados_adicionais_parser(self):
        lines = [
            "INFORMAÇÕES COMPLEMENTARES",
            "ICMS RETIDO POR SUBSTITUICAO TRIBUTARIA CONFORME CONVENIO SEFIN",
            "Gerado em www.meusistema.com.br"
        ]
        parser = DadosAdicionaisParser()
        info, tem_st = parser.parse(lines, info_idx=0)
        self.assertIn("ICMS RETIDO POR SUBSTITUICAO TRIBUTARIA", info)
        self.assertNotIn("Gerado em www", info)
        self.assertTrue(tem_st)


if __name__ == "__main__":
    unittest.main()

