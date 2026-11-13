"""
Esquemas de dados tipados para a extração de DANFEs / Notas Fiscais Eletrônicas (Modelo 55).
Modelagem orientada a domínio com Value Objects imutáveis e composição limpa.
"""

from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class IdentificacaoNFe:
    chave_acesso: str
    numero_nf: Optional[str] = None
    serie: Optional[str] = None
    folha: Optional[str] = None
    tipo_operacao: Optional[str] = None  # 0=Entrada, 1=Saída
    natureza_operacao: Optional[str] = None
    protocolo_autorizacao: Optional[str] = None


@dataclass(frozen=True)
class Emitente:
    emitente_cnpj: Optional[str] = None
    emitente_ie: Optional[str] = None
    emitente_ie_st: Optional[str] = None
    emitente_uf: Optional[str] = None


@dataclass(frozen=True)
class Destinatario:
    destinatario_cnpj_cpf: Optional[str] = None
    destinatario_ie: Optional[str] = None
    destinatario_uf: Optional[str] = None
    data_emissao: Optional[str] = None  # Formato YYYY-MM-DD
    data_saida: Optional[str] = None    # Formato YYYY-MM-DD
    hora_saida: Optional[str] = None


@dataclass(frozen=True)
class TotaisImposto:
    bc_icms: Decimal = Decimal("0.00")
    valor_icms: Decimal = Decimal("0.00")
    bc_icms_st: Decimal = Decimal("0.00")
    valor_icms_st: Decimal = Decimal("0.00")
    valor_imp_importacao: Decimal = Decimal("0.00")
    valor_icms_uf_remet: Decimal = Decimal("0.00")
    valor_fcp_uf_dest: Decimal = Decimal("0.00")
    valor_pis: Decimal = Decimal("0.00")
    valor_total_produtos: Decimal = Decimal("0.00")
    valor_frete: Decimal = Decimal("0.00")
    valor_seguro: Decimal = Decimal("0.00")
    valor_desconto: Decimal = Decimal("0.00")
    outras_despesas: Decimal = Decimal("0.00")
    valor_total_ipi: Decimal = Decimal("0.00")
    valor_icms_uf_dest: Decimal = Decimal("0.00")
    valor_tot_trib: Decimal = Decimal("0.00")
    valor_cofins: Decimal = Decimal("0.00")
    valor_total_nota: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class TransporteNFe:
    modalidade_frete: Optional[str] = None
    transportador_cnpj_cpf: Optional[str] = None
    transportador_uf: Optional[str] = None
    placa_veiculo: Optional[str] = None
    volume_quantidade: Optional[Decimal] = None
    peso_bruto: Optional[Decimal] = None
    peso_liquido: Optional[Decimal] = None


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
    quantidade: Decimal
    valor_unitario: Decimal
    valor_total: Decimal
    desconto: Decimal
    bc_icms: Decimal
    valor_icms: Decimal
    valor_ipi: Decimal
    aliq_icms: Decimal
    aliq_ipi: Decimal
    pagina_arquivo: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NFeDuplicata:
    chave_acesso: str
    numero_duplicata: str
    data_vencimento: Optional[str]
    valor: Decimal
    pagina_arquivo: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NFeDocumento:
    identificacao: IdentificacaoNFe
    emitente: Emitente
    destinatario: Destinatario
    totais: TotaisImposto
    transporte: TransporteNFe
    info_complementares: str
    tem_mencao_icms_st: bool
    pagina_arquivo: int
    arquivo_origem: str

    # Propriedades de conveniência para retrocompatibilidade e acesso direto
    @property
    def chave_acesso(self) -> str:
        return self.identificacao.chave_acesso

    @property
    def numero_nf(self) -> Optional[str]:
        return self.identificacao.numero_nf

    @property
    def serie(self) -> Optional[str]:
        return self.identificacao.serie

    @property
    def folha(self) -> Optional[str]:
        return self.identificacao.folha

    @property
    def tipo_operacao(self) -> Optional[str]:
        return self.identificacao.tipo_operacao

    @property
    def natureza_operacao(self) -> Optional[str]:
        return self.identificacao.natureza_operacao

    @property
    def protocolo_autorizacao(self) -> Optional[str]:
        return self.identificacao.protocolo_autorizacao

    @property
    def emitente_cnpj(self) -> Optional[str]:
        return self.emitente.emitente_cnpj

    @property
    def emitente_ie(self) -> Optional[str]:
        return self.emitente.emitente_ie

    @property
    def emitente_ie_st(self) -> Optional[str]:
        return self.emitente.emitente_ie_st

    @property
    def emitente_uf(self) -> Optional[str]:
        return self.emitente.emitente_uf

    @property
    def destinatario_cnpj_cpf(self) -> Optional[str]:
        return self.destinatario.destinatario_cnpj_cpf

    @property
    def destinatario_ie(self) -> Optional[str]:
        return self.destinatario.destinatario_ie

    @property
    def destinatario_uf(self) -> Optional[str]:
        return self.destinatario.destinatario_uf

    @property
    def data_emissao(self) -> Optional[str]:
        return self.destinatario.data_emissao

    @property
    def data_saida(self) -> Optional[str]:
        return self.destinatario.data_saida

    @property
    def hora_saida(self) -> Optional[str]:
        return self.destinatario.hora_saida

    @property
    def bc_icms(self) -> Decimal:
        return self.totais.bc_icms

    @property
    def valor_icms(self) -> Decimal:
        return self.totais.valor_icms

    @property
    def bc_icms_st(self) -> Decimal:
        return self.totais.bc_icms_st

    @property
    def valor_icms_st(self) -> Decimal:
        return self.totais.valor_icms_st

    @property
    def valor_imp_importacao(self) -> Decimal:
        return self.totais.valor_imp_importacao

    @property
    def valor_icms_uf_remet(self) -> Decimal:
        return self.totais.valor_icms_uf_remet

    @property
    def valor_fcp_uf_dest(self) -> Decimal:
        return self.totais.valor_fcp_uf_dest

    @property
    def valor_pis(self) -> Decimal:
        return self.totais.valor_pis

    @property
    def valor_total_produtos(self) -> Decimal:
        return self.totais.valor_total_produtos

    @property
    def valor_frete(self) -> Decimal:
        return self.totais.valor_frete

    @property
    def valor_seguro(self) -> Decimal:
        return self.totais.valor_seguro

    @property
    def valor_desconto(self) -> Decimal:
        return self.totais.valor_desconto

    @property
    def outras_despesas(self) -> Decimal:
        return self.totais.outras_despesas

    @property
    def valor_total_ipi(self) -> Decimal:
        return self.totais.valor_total_ipi

    @property
    def valor_icms_uf_dest(self) -> Decimal:
        return self.totais.valor_icms_uf_dest

    @property
    def valor_tot_trib(self) -> Decimal:
        return self.totais.valor_tot_trib

    @property
    def valor_cofins(self) -> Decimal:
        return self.totais.valor_cofins

    @property
    def valor_total_nota(self) -> Decimal:
        return self.totais.valor_total_nota

    @property
    def modalidade_frete(self) -> Optional[str]:
        return self.transporte.modalidade_frete

    @property
    def transportador_cnpj_cpf(self) -> Optional[str]:
        return self.transporte.transportador_cnpj_cpf

    @property
    def transportador_uf(self) -> Optional[str]:
        return self.transporte.transportador_uf

    @property
    def placa_veiculo(self) -> Optional[str]:
        return self.transporte.placa_veiculo

    @property
    def volume_quantidade(self) -> Optional[Decimal]:
        return self.transporte.volume_quantidade

    @property
    def peso_bruto(self) -> Optional[Decimal]:
        return self.transporte.peso_bruto

    @property
    def peso_liquido(self) -> Optional[Decimal]:
        return self.transporte.peso_liquido

    def to_dict(self) -> dict:
        """
        Retorna a representação plana (flattened) de todos os dados do documento,
        mantendo estrita compatibilidade com esquemas relacionais CSV e Excel.
        """
        data = {}
        data.update(asdict(self.identificacao))
        data.update(asdict(self.emitente))
        data.update(asdict(self.destinatario))
        data.update(asdict(self.totais))
        data.update(asdict(self.transporte))
        data["info_complementares"] = self.info_complementares
        data["tem_mencao_icms_st"] = self.tem_mencao_icms_st
        data["pagina_arquivo"] = self.pagina_arquivo
        data["arquivo_origem"] = self.arquivo_origem
        return data
