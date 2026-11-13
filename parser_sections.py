"""
Parser estruturado e modular para seções do DANFE (NF-e Modelo 55):
- Identificação da NF-e e Cabeçalho
- Identificação do Emitente e Destinatário
- Faturas e Duplicatas
- Totais e Cálculo do Imposto
- Transporte e Volumes
- Dados Adicionais e Menções a ICMS-ST

Implementado com padrões Strategy e Pipeline para garantir responsabilidade única (SRP),
extensibilidade (OCP) e alta testabilidade.
"""

import re
from decimal import Decimal
from typing import List, Tuple, Optional
from schemas import (
    IdentificacaoNFe,
    Emitente,
    Destinatario,
    TotaisImposto,
    TransporteNFe,
    NFeDocumento,
    NFeDuplicata,
)
from utils import parse_decimal, parse_date_br, clean_spaces


# =====================================================================
# Expressões Regulares Pré-compiladas
# =====================================================================
RE_CHAVE = re.compile(r'\b(\d{4}(?:\s*\d{4}){10})\b')
RE_NF = re.compile(r'N[ºo°\.]+\s*([\d\.]+)')
RE_SERIE = re.compile(r'S[ée]rie\s*(\d+)', re.IGNORECASE)
RE_FOLHA = re.compile(r'Folha\s*(\d+\s*[/de]\s*\d+)', re.IGNORECASE)
RE_OPERACAO = re.compile(r'(\d)\s*-\s*(?:SA[IÍ]DA|ENTRADA)', re.IGNORECASE)
RE_PROTOCOLO = re.compile(
    r'PROTOCOLO DE AUTORIZA[ÇC][ÃA]O DE USO\s*\n.*?\b(\d{15}\s*-\s*\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})\b',
    re.DOTALL | re.IGNORECASE
)
RE_NATUREZA = re.compile(
    r'NATUREZA DA OPERA[ÇC][ÃA]O\s*\n\s*(.*?)(?=\s{2,}\d{15}|\n|$)',
    re.IGNORECASE
)
RE_CNPJ_FORMATTED = re.compile(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b')
RE_DOC_FORMATTED = re.compile(r'\b(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})\b')
RE_IE_NUMERIC = re.compile(r'\b\d{8,14}\b')
RE_UF_EMIT = re.compile(r'\b([A-Z]{2})\s+Fone/Fax:')
RE_DEST_IE = re.compile(r'INSCRIÇÃO ESTADUAL.*?\n.*?\b(\d{8,14})\b', re.DOTALL | re.IGNORECASE)
RE_DEST_UF = re.compile(r'\bUF\s+FONE.*?\n.*?\b([A-Z]{2})\b', re.DOTALL | re.IGNORECASE)
RE_DATA_EMISSAO = re.compile(r'DATA DA EMISSÃO.*?\n.*?\b(\d{2}/\d{2}/\d{4})\b', re.DOTALL | re.IGNORECASE)
RE_DATA_SAIDA = re.compile(r'DATA DA SA[IÍ]DA/ENTRADA.*?\n.*?\b(\d{2}/\d{2}/\d{4})\b', re.DOTALL | re.IGNORECASE)
RE_HORA_SAIDA = re.compile(r'HORA DA SA[IÍ]DA/ENTRADA.*?\n.*?\b(\d{2}:\d{2}(?::\d{2})?)\b', re.DOTALL | re.IGNORECASE)

RE_DUP_NUM = re.compile(r'Num\.?\s*(\S+)')
RE_DUP_VENC = re.compile(r'Venc\.?\s*(\d{2}/\d{2}/\d{4})')
RE_DUP_VAL = re.compile(r'Valor\s*(?:R\$\s*)?([\d.,]+)')

RE_DECIMAL_ROW = re.compile(r'[\d.]*,\d{2}')
RE_FRETE_MODALIDADE = re.compile(r'\b([0-9]-[A-Za-z0-9\s/]+?)(?=\s{2,}|\n|$)')
RE_PLACA = re.compile(r'PLACA DO VE[IÍ]CULO.*?\n.*?\b([A-Z]{3}-?\d[A-Z0-9]\d{2})\b', re.DOTALL | re.IGNORECASE)
RE_ICMS_ST_MENCAO = re.compile(r'\b(?:SUBST(?:ITUI[ÇC][ÃA]O)?|S\.?T\.?|RETIDO|SEFIN|CRE\s+DE)\b', re.IGNORECASE)


def find_line_index(lines: List[str], targets: List[str]) -> int:
    """Encontra o índice da primeira linha que contém um dos termos-alvo."""
    for idx, line in enumerate(lines):
        line_upper = line.upper()
        for t in targets:
            if t.upper() in line_upper:
                return idx
    return -1


# =====================================================================
# Sub-parsers Especializados (SRP)
# =====================================================================
class IdentificacaoParser:
    """Extrai chave de acesso e metadados de identificação da NF-e."""

    def parse(self, text: str) -> Optional[IdentificacaoNFe]:
        m_chave = RE_CHAVE.search(text)
        if not m_chave:
            return None

        chave_acesso = re.sub(r'\s+', '', m_chave.group(1))

        m_nf = RE_NF.search(text)
        numero_nf = clean_spaces(m_nf.group(1).replace('.', '')) if m_nf else None

        m_serie = RE_SERIE.search(text)
        serie = clean_spaces(m_serie.group(1)) if m_serie else None

        m_folha = RE_FOLHA.search(text)
        folha = clean_spaces(m_folha.group(1)) if m_folha else None

        m_operacao = RE_OPERACAO.search(text)
        tipo_operacao = m_operacao.group(1) if m_operacao else None

        m_prot = RE_PROTOCOLO.search(text)
        protocolo_autorizacao = clean_spaces(m_prot.group(1)) if m_prot else None

        m_nat = RE_NATUREZA.search(text)
        natureza_operacao = clean_spaces(m_nat.group(1)) if m_nat else None

        return IdentificacaoNFe(
            chave_acesso=chave_acesso,
            numero_nf=numero_nf,
            serie=serie,
            folha=folha,
            tipo_operacao=tipo_operacao,
            natureza_operacao=natureza_operacao,
            protocolo_autorizacao=protocolo_autorizacao
        )


class EmitenteParser:
    """Extrai os dados cadastrais do emitente a partir do cabeçalho da página."""

    def parse(self, text: str, lines: List[str], dest_idx: int) -> Emitente:
        header_lines = lines[:dest_idx] if dest_idx != -1 else lines[:35]

        emitente_cnpj = None
        emitente_ie = None
        emitente_ie_st = None
        emitente_uf = None

        for i, l in enumerate(header_lines):
            l_upper = l.upper()
            if 'CNPJ' in l_upper and not emitente_cnpj:
                for next_l in header_lines[i+1:i+4]:
                    m = RE_CNPJ_FORMATTED.search(next_l)
                    if m:
                        emitente_cnpj = m.group(0)
                        break
            if 'INSCRIÇÃO ESTADUAL DO SUBST. TRIBUT' in l_upper or 'INSCRIÇÃO ESTADUAL' in l_upper:
                for next_l in header_lines[i+1:i+3]:
                    ies = RE_IE_NUMERIC.findall(next_l)
                    if ies and not emitente_ie:
                        emitente_ie = ies[0]
                        if len(ies) > 1:
                            emitente_ie_st = ies[1]

        m_uf_emit = RE_UF_EMIT.search(text)
        if m_uf_emit:
            emitente_uf = m_uf_emit.group(1)

        return Emitente(
            emitente_cnpj=emitente_cnpj,
            emitente_ie=emitente_ie,
            emitente_ie_st=emitente_ie_st,
            emitente_uf=emitente_uf
        )


class DestinatarioParser:
    """Extrai dados cadastrais e datas/horários do destinatário / remetente."""

    def parse(self, lines: List[str], dest_idx: int) -> Destinatario:
        if dest_idx == -1:
            return Destinatario()

        dest_lines = lines[dest_idx:dest_idx+12]
        dest_text = "\n".join(dest_lines)

        destinatario_cnpj_cpf = None
        m_dest_doc = RE_DOC_FORMATTED.search(dest_text)
        if m_dest_doc:
            destinatario_cnpj_cpf = m_dest_doc.group(0)

        destinatario_ie = None
        m_dest_ie = RE_DEST_IE.search(dest_text)
        if m_dest_ie:
            destinatario_ie = m_dest_ie.group(1)

        destinatario_uf = None
        m_dest_uf = RE_DEST_UF.search(dest_text)
        if m_dest_uf:
            destinatario_uf = m_dest_uf.group(1)

        m_emissao = RE_DATA_EMISSAO.search(dest_text)
        data_emissao = parse_date_br(m_emissao.group(1)) if m_emissao else None

        m_saida = RE_DATA_SAIDA.search(dest_text)
        data_saida = parse_date_br(m_saida.group(1)) if m_saida else None

        m_hora = RE_HORA_SAIDA.search(dest_text)
        hora_saida = m_hora.group(1) if m_hora else None

        return Destinatario(
            destinatario_cnpj_cpf=destinatario_cnpj_cpf,
            destinatario_ie=destinatario_ie,
            destinatario_uf=destinatario_uf,
            data_emissao=data_emissao,
            data_saida=data_saida,
            hora_saida=hora_saida
        )


class DuplicatasParser:
    """Extrai parcelas de pagamento da seção de Fatura / Duplicata."""

    def parse(
        self,
        lines: List[str],
        fat_idx: int,
        calc_idx: int,
        chave_acesso: str,
        page_num: int
    ) -> List[NFeDuplicata]:
        if fat_idx == -1 or calc_idx == -1 or calc_idx <= fat_idx:
            return []

        duplicatas: List[NFeDuplicata] = []
        fat_text = "\n".join(lines[fat_idx:calc_idx])
        num_matches = RE_DUP_NUM.findall(fat_text)
        venc_matches = RE_DUP_VENC.findall(fat_text)
        val_matches = RE_DUP_VAL.findall(fat_text)

        for n, v, val in zip(num_matches, venc_matches, val_matches):
            duplicatas.append(NFeDuplicata(
                chave_acesso=chave_acesso,
                numero_duplicata=clean_spaces(n),
                data_vencimento=parse_date_br(v),
                valor=parse_decimal(val),
                pagina_arquivo=page_num
            ))

        return duplicatas


class TotaisImpostoParser:
    """Extrai as duas linhas da grade de cálculo do imposto e totais da nota."""

    LINE1_TARGETS = ['BASE DE CÁLC', 'BASE DE CALC']
    LINE2_TARGETS = ['VALOR DO FRETE', 'VALOR FRETE']

    def parse(self, lines: List[str], calc_idx: int) -> TotaisImposto:
        if calc_idx == -1:
            return TotaisImposto()

        imposto_l1 = self._extract_numeric_row(lines, calc_idx, self.LINE1_TARGETS, max_lookahead=5)
        imposto_l2 = self._extract_numeric_row(lines, calc_idx, self.LINE2_TARGETS, max_lookahead=8)

        return TotaisImposto(
            bc_icms=imposto_l1[0],
            valor_icms=imposto_l1[1],
            bc_icms_st=imposto_l1[2],
            valor_icms_st=imposto_l1[3],
            valor_imp_importacao=imposto_l1[4],
            valor_icms_uf_remet=imposto_l1[5],
            valor_fcp_uf_dest=imposto_l1[6],
            valor_pis=imposto_l1[7],
            valor_total_produtos=imposto_l1[8],
            valor_frete=imposto_l2[0],
            valor_seguro=imposto_l2[1],
            valor_desconto=imposto_l2[2],
            outras_despesas=imposto_l2[3],
            valor_total_ipi=imposto_l2[4],
            valor_icms_uf_dest=imposto_l2[5],
            valor_tot_trib=imposto_l2[6],
            valor_cofins=imposto_l2[7],
            valor_total_nota=imposto_l2[8]
        )

    def _extract_numeric_row(
        self,
        lines: List[str],
        base_idx: int,
        header_targets: List[str],
        max_lookahead: int
    ) -> List[Decimal]:
        hdr_idx = -1
        limit = min(len(lines), base_idx + max_lookahead)
        for i in range(base_idx + 1, limit):
            l_upper = lines[i].upper()
            if any(t in l_upper for t in header_targets):
                hdr_idx = i
                break

        row: List[Decimal] = [Decimal("0.00")] * 9
        if hdr_idx != -1:
            for off in range(1, 5):
                if hdr_idx + off < len(lines):
                    cand = lines[hdr_idx + off]
                    matches = RE_DECIMAL_ROW.findall(cand)
                    if matches:
                        nums = [parse_decimal(n) for n in matches]
                        if len(nums) >= 9:
                            row = nums[:9]
                        elif len(nums) > 0:
                            row[:len(nums)] = nums
                        break
        return row


class TransporteParser:
    """Extrai informações sobre modalidade de frete, transportador e veículo."""

    def parse(self, lines: List[str], transp_idx: int) -> TransporteNFe:
        if transp_idx == -1:
            return TransporteNFe()

        transp_lines = lines[transp_idx:transp_idx+8]
        transp_text = "\n".join(transp_lines)

        modalidade_frete = None
        m_fr = RE_FRETE_MODALIDADE.search(transp_text)
        if m_fr:
            modalidade_frete = clean_spaces(m_fr.group(1))

        transportador_cnpj_cpf = None
        m_tr_cnpj = RE_DOC_FORMATTED.search(transp_text)
        if m_tr_cnpj:
            transportador_cnpj_cpf = m_tr_cnpj.group(0)

        placa_veiculo = None
        m_placa = RE_PLACA.search(transp_text)
        if m_placa:
            placa_veiculo = m_placa.group(1)

        return TransporteNFe(
            modalidade_frete=modalidade_frete,
            transportador_cnpj_cpf=transportador_cnpj_cpf,
            transportador_uf=None,
            placa_veiculo=placa_veiculo,
            volume_quantidade=None,
            peso_bruto=None,
            peso_liquido=None
        )


class DadosAdicionaisParser:
    """Extrai informações complementares e avalia presença de menção a ICMS-ST."""

    def parse(self, lines: List[str], info_idx: int) -> Tuple[str, bool]:
        if info_idx == -1:
            return "", False

        info_lines = lines[info_idx+1:]
        filtered_lines = [
            l.strip()
            for l in info_lines
            if l.strip() and not l.strip().startswith('Gerado em www.')
        ]
        info_complementares = clean_spaces(" ".join(filtered_lines))
        tem_mencao_icms_st = bool(RE_ICMS_ST_MENCAO.search(info_complementares))

        return info_complementares, tem_mencao_icms_st


# =====================================================================
# Pipeline Orquestrador
# =====================================================================
class NFeSectionPipeline:
    """
    Coordena os sub-parsers das diferentes seções estruturais do documento.
    """

    def __init__(self):
        self.identificacao_parser = IdentificacaoParser()
        self.emitente_parser = EmitenteParser()
        self.destinatario_parser = DestinatarioParser()
        self.duplicatas_parser = DuplicatasParser()
        self.totais_parser = TotaisImpostoParser()
        self.transporte_parser = TransporteParser()
        self.dados_adicionais_parser = DadosAdicionaisParser()

    def parse_page(
        self,
        text: str,
        lines: List[str],
        page_num: int,
        file_name: str
    ) -> Tuple[Optional[NFeDocumento], List[NFeDuplicata]]:
        # 1. Identificação principal (chave de acesso obrigatória)
        identificacao = self.identificacao_parser.parse(text)
        if not identificacao:
            return None, []

        # 2. Localização de âncoras de seções
        dest_idx = find_line_index(lines, ['DESTINATÁRIO / REMETENTE', 'DESTINATARIO / REMETENTE'])
        fat_idx = find_line_index(lines, ['FATURA / DUPLICATA', 'DADOS DA FATURA'])
        calc_idx = find_line_index(lines, ['CÁLCULO DO IMPOSTO', 'CALCULO DO IMPOSTO'])
        transp_idx = find_line_index(lines, ['TRANSPORTADOR / VOLUMES TRANSPORTADOS', 'TRANSPORTADOR/VOLUMES'])
        info_idx = find_line_index(lines, ['INFORMAÇÕES COMPLEMENTARES', 'INFORMACOES COMPLEMENTARES'])

        # 3. Execução dos sub-parsers
        emitente = self.emitente_parser.parse(text, lines, dest_idx)
        destinatario = self.destinatario_parser.parse(lines, dest_idx)
        duplicatas = self.duplicatas_parser.parse(
            lines, fat_idx, calc_idx, identificacao.chave_acesso, page_num
        )
        totais = self.totais_parser.parse(lines, calc_idx)
        transporte = self.transporte_parser.parse(lines, transp_idx)
        info_comp, tem_icms_st = self.dados_adicionais_parser.parse(lines, info_idx)

        # 4. Composição do documento final
        documento = NFeDocumento(
            identificacao=identificacao,
            emitente=emitente,
            destinatario=destinatario,
            totais=totais,
            transporte=transporte,
            info_complementares=info_comp,
            tem_mencao_icms_st=tem_icms_st,
            pagina_arquivo=page_num,
            arquivo_origem=file_name
        )

        return documento, duplicatas


# Instância padrão para uso direto e retrocompatibilidade
_default_pipeline = NFeSectionPipeline()


def parse_document_header_and_totals(
    text: str,
    lines: List[str],
    page_num: int,
    file_name: str
) -> Tuple[Optional[NFeDocumento], List[NFeDuplicata]]:
    """
    Função mantida para total retrocompatibilidade com chamadas existentes.
    Delega a execução para a pipeline de sub-parsers.
    """
    return _default_pipeline.parse_page(text, lines, page_num, file_name)
