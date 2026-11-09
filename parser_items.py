"""
Parser especializado para a tabela de produtos e serviços do DANFE (NF-e Modelo 55).
Suporta regime normal (CST) e Simples Nacional (CSOSN), além de descrições multilinhas
e alinhamento dinâmico de colunas tributárias por proximidade horizontal.
"""

import re
from typing import List, Dict, Any, Optional
from schemas import NFeItem
from utils import parse_decimal, clean_spaces


# =====================================================================
# Expressões Regulares e Constantes Pré-compiladas
# =====================================================================
RE_COL_DESC = re.compile(r'\bDESC\b')
RE_COL_ICMS = re.compile(r'\bICMS\b')
RE_COL_IPI = re.compile(r'\bIPI\b')
RE_ITEM_MAIN = re.compile(r'\b(\d{8})\s+(\d{3,4})\s+(\d{4})\s+([A-Za-z0-9]{2,4})\b')
RE_NUMERIC_TOKENS = re.compile(r'[\d.,]+')

SECTION_TERMINATORS = (
    'DADOS ADICIONAIS',
    'INFORMAÇÕES COMPLEMENTARES',
    'CÁLCULO DO ISSQN',
    'DADOS DO ISSQN'
)

DESCRIPTION_STOP_TERMS = (
    'VALOR',
    'DADOS',
    'FOLHA',
    'CONTINUA'
)

DEFAULT_TAX_KEYS = ('desc', 'bc_icms', 'v_icms', 'v_ipi', 'aliq_icms', 'aliq_ipi')


class ItemTableParser:
    """
    Parser responsável pela identificação, leitura tabular e mapeamento
    de produtos e serviços a partir das linhas de texto da página.
    """

    def parse(self, lines: List[str], chave_acesso: str, page_num: int) -> List[NFeItem]:
        """Localiza o cabeçalho tabular de produtos e extrai os itens da página."""
        header_idx = self._find_table_header(lines)
        if header_idx == -1:
            return []

        header_line = lines[header_idx]
        tipo_tributacao = 'CSOSN' if 'CSOSN' in header_line.upper() else 'CST'

        desc_match = RE_COL_DESC.search(header_line)
        icms_matches = list(RE_COL_ICMS.finditer(header_line))
        ipi_matches = list(RE_COL_IPI.finditer(header_line))

        if not desc_match or len(icms_matches) < 3 or len(ipi_matches) < 2:
            return []

        # Posições horizontais de referência para cálculo de proximidade
        h_cols: Dict[str, int] = {
            'desc': desc_match.end(),
            'bc_icms': icms_matches[0].end(),
            'v_icms': icms_matches[1].end(),
            'v_ipi': ipi_matches[0].end(),
            'aliq_icms': icms_matches[2].end(),
            'aliq_ipi': ipi_matches[1].end(),
        }

        desc_start_pos = desc_match.start()
        raw_items: List[Dict[str, Any]] = []
        current_item: Optional[Dict[str, Any]] = None

        for line in lines[header_idx + 1:]:
            line_upper = line.upper()
            if any(term in line_upper for term in SECTION_TERMINATORS):
                break

            if not line.strip():
                continue

            match_item = RE_ITEM_MAIN.search(line)
            if match_item:
                if current_item:
                    raw_items.append(current_item)

                current_item = self._extract_item_row(
                    line=line,
                    match=match_item,
                    desc_start=desc_start_pos,
                    h_cols=h_cols
                )
            elif current_item:
                # Acumula linhas de detalhe/descrição secundária
                if not any(stop in line_upper for stop in DESCRIPTION_STOP_TERMS):
                    current_item['descricao'] += ' ' + line.strip()

        if current_item:
            raw_items.append(current_item)

        return self._build_item_objects(raw_items, chave_acesso, page_num, tipo_tributacao)

    def _find_table_header(self, lines: List[str]) -> int:
        for idx, line in enumerate(lines):
            line_upper = line.upper()
            if 'CÓDIGO' in line_upper and ('NCM' in line_upper or 'DESCRI' in line_upper):
                return idx
        return -1

    def _extract_item_row(
        self,
        line: str,
        match: re.Match,
        desc_start: int,
        h_cols: Dict[str, int]
    ) -> Dict[str, Any]:
        ncm, cst_csosn, cfop, un = match.groups()

        pre_text = line[:match.start()].strip()
        pre_parts = pre_text.split(maxsplit=1)
        codigo = pre_parts[0] if pre_parts else ''
        descricao = pre_parts[1] if len(pre_parts) > 1 else ''

        # Quantidade, Unitário e Total entre UN e início da coluna DESC
        between_text = line[match.end():desc_start]
        num_tokens = RE_NUMERIC_TOKENS.findall(between_text)
        quant = num_tokens[0] if len(num_tokens) > 0 else '0'
        unit = num_tokens[1] if len(num_tokens) > 1 else '0'
        total = num_tokens[2] if len(num_tokens) > 2 else '0'

        # Segmento das colunas de tributos (offset relativo)
        seg_offset = max(0, desc_start - 5)
        seg_taxes = line[seg_offset:]
        taxes = self._parse_taxes_by_proximity(h_cols, seg_taxes, seg_offset)

        return {
            'codigo': codigo,
            'descricao': descricao,
            'ncm': ncm,
            'cst_csosn': cst_csosn,
            'cfop': cfop,
            'un': un,
            'quant': quant,
            'unit': unit,
            'total': total,
            'taxes': taxes,
        }

    def _parse_taxes_by_proximity(
        self,
        h_cols: Dict[str, int],
        line_segment: str,
        segment_offset: int
    ) -> Dict[str, str]:
        """Associa cada valor numérico ao cabeçalho de imposto mais próximo horizontalmente."""
        matches = list(RE_NUMERIC_TOKENS.finditer(line_segment))
        col_assigned: Dict[str, str] = {name: '0,00' for name in DEFAULT_TAX_KEYS}

        for m in matches:
            num_str = m.group(0)
            num_center = segment_offset + (m.start() + m.end()) / 2
            best_col = min(h_cols.keys(), key=lambda c: abs(h_cols[c] - num_center))
            col_assigned[best_col] = num_str

        return col_assigned

    def _build_item_objects(
        self,
        raw_items: List[Dict[str, Any]],
        chave_acesso: str,
        page_num: int,
        tipo_tributacao: str
    ) -> List[NFeItem]:
        items: List[NFeItem] = []
        for idx, it in enumerate(raw_items, start=1):
            taxes = it['taxes']
            item = NFeItem(
                chave_acesso=chave_acesso,
                numero_item=idx,
                codigo_produto=clean_spaces(it['codigo']),
                descricao=clean_spaces(it['descricao']),
                ncm=clean_spaces(it['ncm']),
                cst_csosn=clean_spaces(it['cst_csosn']),
                tipo_tributacao=tipo_tributacao,
                cfop=clean_spaces(it['cfop']),
                unidade=clean_spaces(it['un']),
                quantidade=parse_decimal(it['quant']),
                valor_unitario=parse_decimal(it['unit']),
                valor_total=parse_decimal(it['total']),
                desconto=parse_decimal(taxes.get('desc')),
                bc_icms=parse_decimal(taxes.get('bc_icms')),
                valor_icms=parse_decimal(taxes.get('v_icms')),
                valor_ipi=parse_decimal(taxes.get('v_ipi')),
                aliq_icms=parse_decimal(taxes.get('aliq_icms')),
                aliq_ipi=parse_decimal(taxes.get('aliq_ipi')),
                pagina_arquivo=page_num
            )
            items.append(item)
        return items


# Instância padrão para conveniência e retrocompatibilidade
_default_item_parser = ItemTableParser()


def extract_items_from_page(lines: List[str], chave_acesso: str, page_num: int) -> List[NFeItem]:
    """Função mantida para total compatibilidade delegando para a classe especializada."""
    return _default_item_parser.parse(lines, chave_acesso, page_num)
