"""
Parser para seções estruturais do DANFE:
- Cabeçalho e Identificação da NF-e
- Identificação do Emitente e Destinatário
- Duplicatas e Faturas
- Totais e Cálculo do Imposto
- Transportador e Volumes
- Dados Adicionais e Informações Complementares (com detecção de ICMS-ST)
"""

import re
from typing import List, Tuple, Optional
from schemas import NFeDocumento, NFeDuplicata
from utils import parse_decimal, parse_date_br, clean_spaces


def parse_document_header_and_totals(
    text: str,
    lines: List[str],
    page_num: int,
    file_name: str
) -> Tuple[Optional[NFeDocumento], List[NFeDuplicata]]:
    """
    Extrai as seções estruturais do documento da página.
    """
    # 1. Chave de Acesso (44 dígitos)
    m_chave = re.search(r'\b(\d{4}(?:\s*\d{4}){10})\b', text)
    if not m_chave:
        return None, []
    chave_acesso = re.sub(r'\s+', '', m_chave.group(1))

    # 2. Número da NF-e e Série
    m_nf = re.search(r'N[ºo°\.]+\s*([\d\.]+)', text)
    numero_nf = clean_spaces(m_nf.group(1).replace('.', '')) if m_nf else None

    m_serie = re.search(r'S[ée]rie\s*(\d+)', text, re.IGNORECASE)
    serie = clean_spaces(m_serie.group(1)) if m_serie else None

    m_folha = re.search(r'Folha\s*(\d+\s*[/de]\s*\d+)', text, re.IGNORECASE)
    folha = clean_spaces(m_folha.group(1)) if m_folha else None

    # Tipo de Operação (0 - Entrada, 1 - Saída)
    m_operacao = re.search(r'(\d)\s*-\s*(?:SA[IÍ]DA|ENTRADA)', text, re.IGNORECASE)
    tipo_operacao = m_operacao.group(1) if m_operacao else None

    # Protocolo de Autorização
    m_prot = re.search(
        r'PROTOCOLO DE AUTORIZA[ÇC][ÃA]O DE USO\s*\n.*?\b(\d{15}\s*-\s*\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})\b',
        text,
        re.DOTALL | re.IGNORECASE
    )
    protocolo_autorizacao = clean_spaces(m_prot.group(1)) if m_prot else None

    # Natureza da Operação
    m_nat = re.search(
        r'NATUREZA DA OPERA[ÇC][ÃA]O\s*\n\s*(.*?)(?=\s{2,}\d{15}|\n|$)',
        text,
        re.IGNORECASE
    )
    natureza_operacao = clean_spaces(m_nat.group(1)) if m_nat else None

    # 3. Emitente
    # Busca CNPJ e IE antes da seção DESTINATÁRIO
    dest_idx = _find_line_index(lines, ['DESTINATÁRIO / REMETENTE', 'DESTINATARIO / REMETENTE'])
    header_lines = lines[:dest_idx] if dest_idx != -1 else lines[:35]

    emitente_cnpj = None
    emitente_ie = None
    emitente_ie_st = None
    emitente_uf = None

    for i, l in enumerate(header_lines):
        if 'CNPJ' in l.upper() and not emitente_cnpj:
            for next_l in header_lines[i+1:i+4]:
                m = re.search(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b', next_l)
                if m:
                    emitente_cnpj = m.group(0)
                    break
        if 'INSCRIÇÃO ESTADUAL DO SUBST. TRIBUT' in l.upper() or 'INSCRIÇÃO ESTADUAL' in l.upper():
            for next_l in header_lines[i+1:i+3]:
                # Busca IE numérica
                ies = re.findall(r'\b\d{8,14}\b', next_l)
                if ies and not emitente_ie:
                    emitente_ie = ies[0]
                    if len(ies) > 1:
                        emitente_ie_st = ies[1]

    # UF do Emitente
    m_uf_emit = re.search(r'\b([A-Z]{2})\s+Fone/Fax:', text)
    if m_uf_emit:
        emitente_uf = m_uf_emit.group(1)

    # 4. Destinatário / Remetente
    destinatario_cnpj_cpf = None
    destinatario_ie = None
    destinatario_uf = None
    data_emissao = None
    data_saida = None
    hora_saida = None

    if dest_idx != -1:
        dest_lines = lines[dest_idx:dest_idx+12]
        dest_text = "\n".join(dest_lines)

        m_dest_doc = re.search(r'\b(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})\b', dest_text)
        if m_dest_doc:
            destinatario_cnpj_cpf = m_dest_doc.group(0)

        # IE Destinatário
        m_dest_ie = re.search(r'INSCRIÇÃO ESTADUAL.*?\n.*?\b(\d{8,14})\b', dest_text, re.DOTALL | re.IGNORECASE)
        if m_dest_ie:
            destinatario_ie = m_dest_ie.group(1)

        # UF Destinatário
        m_dest_uf = re.search(r'\bUF\s+FONE.*?\n.*?\b([A-Z]{2})\b', dest_text, re.DOTALL | re.IGNORECASE)
        if m_dest_uf:
            destinatario_uf = m_dest_uf.group(1)

        # Datas e Horários
        m_emissao = re.search(r'DATA DA EMISSÃO.*?\n.*?\b(\d{2}/\d{2}/\d{4})\b', dest_text, re.DOTALL | re.IGNORECASE)
        if m_emissao:
            data_emissao = parse_date_br(m_emissao.group(1))

        m_saida = re.search(r'DATA DA SA[IÍ]DA/ENTRADA.*?\n.*?\b(\d{2}/\d{2}/\d{4})\b', dest_text, re.DOTALL | re.IGNORECASE)
        if m_saida:
            data_saida = parse_date_br(m_saida.group(1))

        m_hora = re.search(r'HORA DA SA[IÍ]DA/ENTRADA.*?\n.*?\b(\d{2}:\d{2}(?::\d{2})?)\b', dest_text, re.DOTALL | re.IGNORECASE)
        if m_hora:
            hora_saida = m_hora.group(1)

    # 5. Faturas / Duplicatas
    duplicatas: List[NFeDuplicata] = []
    fat_idx = _find_line_index(lines, ['FATURA / DUPLICATA', 'DADOS DA FATURA'])
    calc_idx = _find_line_index(lines, ['CÁLCULO DO IMPOSTO', 'CALCULO DO IMPOSTO'])

    if fat_idx != -1 and calc_idx != -1 and calc_idx > fat_idx:
        fat_text = "\n".join(lines[fat_idx:calc_idx])
        num_matches = re.findall(r'Num\.?\s*(\S+)', fat_text)
        venc_matches = re.findall(r'Venc\.?\s*(\d{2}/\d{2}/\d{4})', fat_text)
        val_matches = re.findall(r'Valor\s*(?:R\$\s*)?([\d.,]+)', fat_text)

        for n, v, val in zip(num_matches, venc_matches, val_matches):
            dup = NFeDuplicata(
                chave_acesso=chave_acesso,
                numero_duplicata=clean_spaces(n),
                data_vencimento=parse_date_br(v),
                valor=parse_decimal(val),
                pagina_arquivo=page_num
            )
            duplicatas.append(dup)

    # 6. Cálculo do Imposto (Totais)
    imposto_l1: List[float] = [0.0] * 9
    imposto_l2: List[float] = [0.0] * 9

    if calc_idx != -1:
        # Localiza linha do cabeçalho 1 (Base de Cálculo do ICMS ...)
        hdr1_idx = -1
        for i in range(calc_idx + 1, min(len(lines), calc_idx + 5)):
            if 'BASE DE CÁLC' in lines[i].upper() or 'BASE DE CALC' in lines[i].upper():
                hdr1_idx = i
                break

        # Linha 1 de valores numéricos (primeira linha com números após o cabeçalho 1)
        if hdr1_idx != -1:
            for off in range(1, 5):
                if hdr1_idx + off < len(lines):
                    cand = lines[hdr1_idx + off]
                    nums = [parse_decimal(n) for n in re.findall(r'[\d.]*,\d{2}', cand)]
                    if nums:
                        if len(nums) >= 9:
                            imposto_l1 = nums[:9]
                        elif len(nums) > 0:
                            imposto_l1[:len(nums)] = nums
                        break

        # Localiza linha do cabeçalho 2 (Valor do Frete ...)
        hdr2_idx = -1
        for i in range(calc_idx + 1, min(len(lines), calc_idx + 8)):
            if 'VALOR DO FRETE' in lines[i].upper() or 'VALOR FRETE' in lines[i].upper():
                hdr2_idx = i
                break

        # Linha 2 de valores numéricos (primeira linha com números após o cabeçalho 2)
        if hdr2_idx != -1:
            for off in range(1, 5):
                if hdr2_idx + off < len(lines):
                    cand = lines[hdr2_idx + off]
                    nums = [parse_decimal(n) for n in re.findall(r'[\d.]*,\d{2}', cand)]
                    if nums:
                        if len(nums) >= 9:
                            imposto_l2 = nums[:9]
                        elif len(nums) > 0:
                            imposto_l2[:len(nums)] = nums
                        break

    # Mapeamento explícito das duas linhas de cálculo de imposto
    bc_icms = imposto_l1[0]
    valor_icms = imposto_l1[1]
    bc_icms_st = imposto_l1[2]
    valor_icms_st = imposto_l1[3]
    valor_imp_importacao = imposto_l1[4]
    valor_icms_uf_remet = imposto_l1[5]
    valor_fcp_uf_dest = imposto_l1[6]
    valor_pis = imposto_l1[7]
    valor_total_produtos = imposto_l1[8]

    valor_frete = imposto_l2[0]
    valor_seguro = imposto_l2[1]
    valor_desconto = imposto_l2[2]
    outras_despesas = imposto_l2[3]
    valor_total_ipi = imposto_l2[4]
    valor_icms_uf_dest = imposto_l2[5]
    valor_tot_trib = imposto_l2[6]
    valor_cofins = imposto_l2[7]
    valor_total_nota = imposto_l2[8]

    # 7. Transporte
    modalidade_frete = None
    transportador_cnpj_cpf = None
    transportador_uf = None
    placa_veiculo = None
    volume_quantidade = None
    peso_bruto = None
    peso_liquido = None

    transp_idx = _find_line_index(lines, ['TRANSPORTADOR / VOLUMES TRANSPORTADOS', 'TRANSPORTADOR/VOLUMES'])
    if transp_idx != -1:
        transp_lines = lines[transp_idx:transp_idx+8]
        transp_text = "\n".join(transp_lines)

        m_fr = re.search(r'\b([0-9]-[A-Za-z0-9\s/]+?)(?=\s{2,}|\n|$)', transp_text)
        if m_fr:
            modalidade_frete = clean_spaces(m_fr.group(1))

        m_tr_cnpj = re.search(r'\b(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})\b', transp_text)
        if m_tr_cnpj:
            transportador_cnpj_cpf = m_tr_cnpj.group(0)

        m_placa = re.search(r'PLACA DO VE[IÍ]CULO.*?\n.*?\b([A-Z]{3}-?\d[A-Z0-9]\d{2})\b', transp_text, re.DOTALL | re.IGNORECASE)
        if m_placa:
            placa_veiculo = m_placa.group(1)

    # 8. Dados Adicionais / Informações Complementares
    info_idx = _find_line_index(lines, ['INFORMAÇÕES COMPLEMENTARES', 'INFORMACOES COMPLEMENTARES'])
    info_complementares = ""
    if info_idx != -1:
        info_lines = lines[info_idx+1:]
        # Remove linha final de propaganda/emissão se existir
        filtered_lines = [l.strip() for l in info_lines if l.strip() and not l.strip().startswith('Gerado em www.')]
        info_complementares = clean_spaces(" ".join(filtered_lines))

    tem_mencao_icms_st = bool(re.search(
        r'\b(?:SUBST(?:ITUI[ÇC][ÃA]O)?|S\.?T\.?|RETIDO|SEFIN|CRE\s+DE)\b',
        info_complementares,
        re.IGNORECASE
    ))

    doc = NFeDocumento(
        chave_acesso=chave_acesso,
        numero_nf=numero_nf,
        serie=serie,
        folha=folha,
        tipo_operacao=tipo_operacao,
        natureza_operacao=natureza_operacao,
        protocolo_autorizacao=protocolo_autorizacao,
        data_emissao=data_emissao,
        data_saida=data_saida,
        hora_saida=hora_saida,
        emitente_cnpj=emitente_cnpj,
        emitente_ie=emitente_ie,
        emitente_ie_st=emitente_ie_st,
        emitente_uf=emitente_uf,
        destinatario_cnpj_cpf=destinatario_cnpj_cpf,
        destinatario_ie=destinatario_ie,
        destinatario_uf=destinatario_uf,
        bc_icms=bc_icms,
        valor_icms=valor_icms,
        bc_icms_st=bc_icms_st,
        valor_icms_st=valor_icms_st,
        valor_imp_importacao=valor_imp_importacao,
        valor_icms_uf_remet=valor_icms_uf_remet,
        valor_fcp_uf_dest=valor_fcp_uf_dest,
        valor_pis=valor_pis,
        valor_total_produtos=valor_total_produtos,
        valor_frete=valor_frete,
        valor_seguro=valor_seguro,
        valor_desconto=valor_desconto,
        outras_despesas=outras_despesas,
        valor_total_ipi=valor_total_ipi,
        valor_icms_uf_dest=valor_icms_uf_dest,
        valor_tot_trib=valor_tot_trib,
        valor_cofins=valor_cofins,
        valor_total_nota=valor_total_nota,
        modalidade_frete=modalidade_frete,
        transportador_cnpj_cpf=transportador_cnpj_cpf,
        transportador_uf=transportador_uf,
        placa_veiculo=placa_veiculo,
        volume_quantidade=volume_quantidade,
        peso_bruto=peso_bruto,
        peso_liquido=peso_liquido,
        info_complementares=info_complementares,
        tem_mencao_icms_st=tem_mencao_icms_st,
        pagina_arquivo=page_num,
        arquivo_origem=file_name
    )

    return doc, duplicatas


def _find_line_index(lines: List[str], targets: List[str]) -> int:
    """
    Encontra o índice da primeira linha que contém um dos termos-alvo.
    """
    for idx, line in enumerate(lines):
        for t in targets:
            if t.upper() in line.upper():
                return idx
    return -1
