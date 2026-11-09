"""
Esquemas de dados tipados para a extração de DANFEs / Notas Fiscais Eletrônicas (Modelo 55).
Contém apenas definições de classes e campos sem nenhum dado pessoal.
"""

from dataclasses import dataclass, asdict, field
from typing import List, Optional


@dataclass
class NFeItem:
    chave_acesso: str
    numero_item: int
    codigo_produto: str
    descricao: str
    ncm: str
    cst_csosn: str
    tipo_tributacao: str  # 'CST' ou 'CSOSN'
    cfop: str
    unidade: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    desconto: float
    bc_icms: float
    valor_icms: float
    valor_ipi: float
    aliq_icms: float
    aliq_ipi: float
    pagina_arquivo: int

    def to_dict(self):
        return asdict(self)


@dataclass
class NFeDuplicata:
    chave_acesso: str
    numero_duplicata: str
    data_vencimento: Optional[str]
    valor: float
    pagina_arquivo: int

    def to_dict(self):
        return asdict(self)


@dataclass
class NFeDocumento:
    chave_acesso: str
    numero_nf: Optional[str]
    serie: Optional[str]
    folha: Optional[str]
    tipo_operacao: Optional[str]  # 0=Entrada, 1=Saída
    natureza_operacao: Optional[str]
    protocolo_autorizacao: Optional[str]
    data_emissao: Optional[str]  # Formato YYYY-MM-DD
    data_saida: Optional[str]    # Formato YYYY-MM-DD
    hora_saida: Optional[str]

    # Emitente
    emitente_cnpj: Optional[str]
    emitente_ie: Optional[str]
    emitente_ie_st: Optional[str]
    emitente_uf: Optional[str]

    # Destinatário
    destinatario_cnpj_cpf: Optional[str]
    destinatario_ie: Optional[str]
    destinatario_uf: Optional[str]

    # Cálculo do Imposto (Totais)
    bc_icms: float
    valor_icms: float
    bc_icms_st: float
    valor_icms_st: float
    valor_imp_importacao: float
    valor_icms_uf_remet: float
    valor_fcp_uf_dest: float
    valor_pis: float
    valor_total_produtos: float
    valor_frete: float
    valor_seguro: float
    valor_desconto: float
    outras_despesas: float
    valor_total_ipi: float
    valor_icms_uf_dest: float
    valor_tot_trib: float
    valor_cofins: float
    valor_total_nota: float

    # Transporte
    modalidade_frete: Optional[str]
    transportador_cnpj_cpf: Optional[str]
    transportador_uf: Optional[str]
    placa_veiculo: Optional[str]
    volume_quantidade: Optional[float]
    peso_bruto: Optional[float]
    peso_liquido: Optional[float]

    # Dados Adicionais / ICMS-ST
    info_complementares: str
    tem_mencao_icms_st: bool
    pagina_arquivo: int
    arquivo_origem: str

    def to_dict(self):
        return asdict(self)
