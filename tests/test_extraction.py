"""
Testes automatizados de validação estrutural do extrator de DANFEs.
Utiliza dados sintéticos mockados para garantir isolamento e integridade sem expor dados reais.
"""

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from schemas import NFeDocumento, NFeItem, NFeDuplicata
from utils import parse_decimal, parse_date_br, clean_spaces
from parser_sections import parse_document_header_and_totals
from parser_items import extract_items_from_page
from exporter import export_to_csv_and_excel


MOCK_DANFE_PAGE = """DANFE
Documento Auxiliar da Nota Fiscal Eletrônica
1 - SAÍDA
Nº 000.123.456
Série 1
Folha 1/1
CHAVE DE ACESSO
1111 2222 3333 4444 5555 6666 7777 8888 9999 0000 1111
PROTOCOLO DE AUTORIZAÇÃO DE USO
123456789012345 - 01/01/2023 10:00:00
NATUREZA DA OPERAÇÃO
VENDA DE MERCADORIAS
EMITENTE MODELO LTDA
RO Fone/Fax: (69) 0000-0000
CNPJ
12.345.678/0001-90
INSCRIÇÃO ESTADUAL
12345678901234
DESTINATÁRIO / REMETENTE
NOME / RAZÃO SOCIAL                                CNPJ/CPF               DATA DA EMISSÃO
DESTINATARIO MODELO LTDA                           98.765.432/0001-10     01/01/2023
INSCRIÇÃO ESTADUAL       UF FONE / FAX             DATA DA SAÍDA/ENTRADA  HORA DA SAÍDA/ENTRADA
98765432101234           RO (69) 1111-2222         01/01/2023             10:30:00
FATURA / DUPLICATA
Num. 001 Venc. 15/01/2023 Valor 1500,00
CÁLCULO DO IMPOSTO
BASE DE CÁLCULO DO ICMS VALOR DO ICMS BASE CÁLC. ICMS S.T. VALOR DO ICMS SUBST. V. IMP. IMPORTAÇÃO V. ICMS UF REMET. V. FCP UF DEST. VALOR DO PIS VALOR TOTAL DOS PRODUTOS
1.000,00 180,00 0,00 0,00 0,00 0,00 0,00 16,50 1.500,00
VALOR DO FRETE VALOR DO SEGURO DESCONTO OUTRAS DESPESAS VALOR TOTAL DO IPI V. ICMS UF DEST. V. TOT. TRIB. VALOR DA COFINS VALOR TOTAL DA NOTA
0,00 0,00 0,00 0,00 0,00 0,00 0,00 76,00 1.500,00
TRANSPORTADOR / VOLUMES TRANSPORTADOS
0-Emitente
CNPJ/CPF
11.222.333/0001-44
PLACA DO VEÍCULO
ABC-1234
DADOS DOS PRODUTOS / SERVIÇOS
CÓDIGO    DESCRIÇÃO                NCM/SH   CST  CFOP UN QUANT. V.UNIT  V.TOTAL   DESC.   B.CÁLC ICMS   VALOR ICMS   VALOR IPI   ALÍQ. ICMS   ALÍQ. IPI
PROD01    PRODUTO TESTE MODELO A   84099190 000  5102 UN 10     100,00  1.000,00  0,00     1.000,00      180,00        0,00        18,00        0,00
          DETALHE ADICIONAL DO PRODUTO
PROD02    PRODUTO TESTE MODELO B   84099999 0102 5102 PC 5      100,00    500,00  0,00         0,00        0,00        0,00         0,00        0,00
DADOS ADICIONAIS
INFORMAÇÕES COMPLEMENTARES
DOCUMENTO EMITIDO COM REFERENCIA A RETIDO ICMS SUBST CONFORME DECRETO SEFIN
"""


class TestDanfeExtractorSynthetic(unittest.TestCase):
    def setUp(self):
        self.lines = MOCK_DANFE_PAGE.splitlines()

    def test_utils(self):
        """Valida utilitários de parsing numérico e de data."""
        self.assertEqual(parse_decimal("1.234,56"), 1234.56)
        self.assertEqual(parse_decimal("0,00"), 0.0)
        self.assertEqual(parse_decimal(None), 0.0)
        self.assertEqual(parse_decimal("invalid"), 0.0)
        self.assertEqual(parse_date_br("15/01/2023"), "2023-01-15")
        self.assertIsNone(parse_date_br(None))
        self.assertEqual(clean_spaces("  texto   com    espaços  "), "texto com espaços")

    def test_header_and_totals_parsing(self):
        """Valida extração das seções estruturais do cabeçalho, totais e duplicatas."""
        doc, duplicatas = parse_document_header_and_totals(
            text=MOCK_DANFE_PAGE,
            lines=self.lines,
            page_num=1,
            file_name="mock_danfe.pdf"
        )
        self.assertIsNotNone(doc)
        self.assertEqual(doc.chave_acesso, "11112222333344445555666677778888999900001111")
        self.assertEqual(len(doc.chave_acesso), 44)
        self.assertEqual(doc.numero_nf, "000123456")
        self.assertEqual(doc.serie, "1")
        self.assertEqual(doc.tipo_operacao, "1")
        self.assertEqual(doc.data_emissao, "2023-01-01")
        self.assertEqual(doc.data_saida, "2023-01-01")
        self.assertEqual(doc.hora_saida, "10:30:00")
        self.assertEqual(doc.emitente_cnpj, "12.345.678/0001-90")
        self.assertEqual(doc.destinatario_cnpj_cpf, "98.765.432/0001-10")
        self.assertEqual(doc.destinatario_uf, "RO")

        # Totais
        self.assertEqual(doc.bc_icms, 1000.0)
        self.assertEqual(doc.valor_icms, 180.0)
        self.assertEqual(doc.valor_pis, 16.50)
        self.assertEqual(doc.valor_cofins, 76.00)
        self.assertEqual(doc.valor_total_produtos, 1500.0)
        self.assertEqual(doc.valor_total_nota, 1500.0)

        # Menção a ICMS-ST
        self.assertTrue(doc.tem_mencao_icms_st)

        # Duplicata
        self.assertEqual(len(duplicatas), 1)
        self.assertEqual(duplicatas[0].numero_duplicata, "001")
        self.assertEqual(duplicatas[0].data_vencimento, "2023-01-15")
        self.assertEqual(duplicatas[0].valor, 1500.0)

    def test_items_parsing(self):
        """Valida extração dos itens tabulares, suportando multilinhas e regimes tributários."""
        items = extract_items_from_page(
            lines=self.lines,
            chave_acesso="11112222333344445555666677778888999900001111",
            page_num=1
        )
        self.assertEqual(len(items), 2)

        # Item 1: CST
        it1 = items[0]
        self.assertEqual(it1.codigo_produto, "PROD01")
        self.assertIn("DETALHE ADICIONAL DO PRODUTO", it1.descricao)
        self.assertEqual(it1.ncm, "84099190")
        self.assertEqual(it1.cst_csosn, "000")
        self.assertEqual(it1.cfop, "5102")
        self.assertEqual(it1.quantidade, 10.0)
        self.assertEqual(it1.valor_unitario, 100.0)
        self.assertEqual(it1.valor_total, 1000.0)
        self.assertEqual(it1.bc_icms, 1000.0)
        self.assertEqual(it1.valor_icms, 180.0)

        # Item 2: CSOSN
        it2 = items[1]
        self.assertEqual(it2.codigo_produto, "PROD02")
        self.assertEqual(it2.cst_csosn, "0102")
        self.assertEqual(it2.tipo_tributacao, "CST")  # Cabeçalho da página continha CST
        self.assertEqual(it2.valor_total, 500.0)

    def test_exporter(self):
        """Valida exportação para arquivos CSV e Excel."""
        doc, duplicatas = parse_document_header_and_totals(
            text=MOCK_DANFE_PAGE,
            lines=self.lines,
            page_num=1,
            file_name="mock_danfe.pdf"
        )
        items = extract_items_from_page(
            lines=self.lines,
            chave_acesso=doc.chave_acesso,
            page_num=1
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = export_to_csv_and_excel(
                documentos=[doc],
                itens=items,
                duplicatas=duplicatas,
                output_dir=tmp_dir,
                export_excel=True
            )
            self.assertTrue(os.path.isfile(paths["documentos_csv"]))
            self.assertTrue(os.path.isfile(paths["itens_csv"]))
            self.assertTrue(os.path.isfile(paths["duplicatas_csv"]))
            if "excel" in paths:
                self.assertTrue(os.path.isfile(paths["excel"]))


if __name__ == "__main__":
    unittest.main()
