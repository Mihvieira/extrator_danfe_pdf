"""
Parser especializado para a tabela de produtos e serviços do DANFE (NF-e Modelo 55).
Suporta regime normal (CST) e Simples Nacional (CSOSN), além de descrições multilinha.
"""

import re
from typing import List, Dict, Any, Tuple
from schemas import NFeItem
from utils import parse_decimal, clean_spaces


def extract_items_from_page(lines: List[str], chave_acesso: str, page_num: int) -> List[NFeItem]:
    """
    Localiza o cabeçalho tabular de produtos e extrai os itens da página.
    """
    h2_idx = -1
    for i, l in enumerate(lines):
        if 'CÓDIGO' in l.upper() and ('NCM' in l.upper() or 'DESCRI' in l.upper()):
            h2_idx = i
            break

    if h2_idx == -1:
        return []

    h2 = lines[h2_idx]
    tipo_tributacao = 'CSOSN' if 'CSOSN' in h2.upper() else 'CST'

    desc_m = re.search(r'\bDESC\b', h2)
    icms_m = list(re.finditer(r'\bICMS\b', h2))
    ipi_m = list(re.finditer(r'\bIPI\b', h2))

    if not desc_m or len(icms_m) < 3 or len(ipi_m) < 2:
        return []

    # Posições de referência para mapeamento por proximidade
    h_cols = {
        'desc': desc_m.end(),
        'bc_icms': icms_m[0].end(),
        'v_icms': icms_m[1].end(),
        'v_ipi': ipi_m[0].end(),
        'aliq_icms': icms_m[2].end(),
        'aliq_ipi': ipi_m[1].end()
    }

    raw_items: List[Dict[str, Any]] = []
    current_item: Dict[str, Any] = None

    for line in lines[h2_idx + 1:]:
        # Término da tabela de itens ao atingir rodapé ou próxima seção
        if any(sec in line.upper() for sec in ['DADOS ADICIONAIS', 'INFORMAÇÕES COMPLEMENTARES', 'CÁLCULO DO ISSQN', 'DADOS DO ISSQN']):
            break

        if not line.strip():
            continue

        # Regex para linha principal de produto: NCM (8 dig) + CST/CSOSN (3-4 dig) + CFOP (4 dig) + UN (2-4 char)
        m_item = re.search(r'\b(\d{8})\s+(\d{3,4})\s+(\d{4})\s+([A-Za-z0-9]{2,4})\b', line)

        if m_item:
            if current_item:
                raw_items.append(current_item)

            ncm, cst_csosn, cfop, un = m_item.groups()

            # Código e início da descrição antes do NCM
            pre_text = line[:m_item.start()].strip()
            pre_parts = pre_text.split(maxsplit=1)
            codigo = pre_parts[0] if pre_parts else ''
            descricao = pre_parts[1] if len(pre_parts) > 1 else ''

            # Quantidade, Unitário e Total entre UN e início do Desconto
            between = line[m_item.end():desc_m.start()]
            num_tokens = re.findall(r'[\d.,]+', between)
            quant = num_tokens[0] if len(num_tokens) > 0 else '0'
            unit = num_tokens[1] if len(num_tokens) > 1 else '0'
            total = num_tokens[2] if len(num_tokens) > 2 else '0'

            # Segmento de tributos da linha (a partir de DESC)
            seg_taxes = line[desc_m.start() - 5:]
            seg_offset = desc_m.start() - 5

            tax_vals = _parse_taxes_by_proximity(h_cols, seg_taxes, seg_offset)

            current_item = {
                'codigo': codigo,
                'descricao': descricao,
                'ncm': ncm,
                'cst_csosn': cst_csosn,
                'cfop': cfop,
                'un': un,
                'quant': quant,
                'unit': unit,
                'total': total,
                'taxes': tax_vals
            }
        elif current_item:
            # Continuação da descrição do produto (linhas complementares)
            if not any(stop in line.upper() for stop in ['VALOR', 'DADOS', 'FOLHA', 'CONTINUA']):
                current_item['descricao'] += ' ' + line.strip()

    if current_item:
        raw_items.append(current_item)

    # Conversão para dataclasses tipadas
    items_objs: List[NFeItem] = []
    for idx, it in enumerate(raw_items, start=1):
        taxes = it['taxes']
        item_obj = NFeItem(
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
        items_objs.append(item_obj)

    return items_objs


def _parse_taxes_by_proximity(h_cols: Dict[str, int], line_segment: str, segment_offset: int) -> Dict[str, str]:
    """
    Associa cada valor numérico ao cabeçalho de imposto mais próximo em termos de coordenada horizontal.
    """
    matches = list(re.finditer(r'[\d.,]+', line_segment))
    col_assigned = {name: '0,00' for name in ['desc', 'bc_icms', 'v_icms', 'v_ipi', 'aliq_icms', 'aliq_ipi']}

    for m in matches:
        num_str = m.group(0)
        num_center = segment_offset + (m.start() + m.end()) / 2
        best_col = min(h_cols.keys(), key=lambda c: abs(h_cols[c] - num_center))
        col_assigned[best_col] = num_str

    return col_assigned
