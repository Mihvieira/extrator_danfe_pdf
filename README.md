# Extrator de Dados de Notas Fiscais Eletrônicas (DANFE Modelo 55)

Módulo em Python projetado para extração e estruturação automatizada de dados fiscais a partir de Documentos Auxiliares da Nota Fiscal Eletrônica (DANFE) em formato PDF, com tratamento posicional e suporte às variações de layouts vigentes entre os anos de 2017 e 2024.

---

## 1. Visão Geral da Arquitetura

O extrator utiliza o utilitário nativo de alta performance `pdftotext` (Poppler) em modo colunar (`-layout`), processando centenas de páginas em poucos segundos sem necessidade de OCR ou dependências binárias complexas.

### Estrutura do Módulo

```
extrator_danfe_pdf/
├── README.md               # Documentação técnica e guia de execução
├── requirements.txt        # Dependências Python (pandas, openpyxl)
├── schemas.py              # Classes tipadas de dados (NFeDocumento, NFeItem, NFeDuplicata)
├── utils.py                # Utilitários de conversão numérica e sanitização
├── pdf_engine.py           # Motor de extração de texto estruturado
├── parser_sections.py      # Extração de Cabeçalho, Totais, Impostos e Dados Adicionais
├── parser_items.py         # Extração tabular de produtos/serviços com suporte a multilinhas
├── exporter.py             # Exportador relacional para CSV e Excel
├── main.py                 # Interface de Linha de Comando (CLI)
└── tests/                  # Testes automatizados de validação estrutural
```

---

## 2. Tratamento das Variações de Layout (2017–2024)

1. **Regime Normal (CST) vs. Simples Nacional (CSOSN):**
   * O parser detecta dinamicamente se o cabeçalho tabular contém a coluna `O/CST` (3 dígitos: origem + tributação) ou `O/CSOSN` (4 dígitos: origem + operação no Simples Nacional), preenchendo adequadamente o campo `tipo_tributacao`.
2. **Campos Estendidos de Imposto (EC 87/2015 & NT 2015.003 / 2016.002):**
   * Suporte às colunas de Partilha do ICMS interestadual (`V. ICMS UF REMET.`, `V. ICMS UF DEST.`, `V. FCP UF DEST.`), além de `V. TOT. TRIB.` (Lei 12.741/2012).
3. **Mapeamento Posicional por Proximidade:**
   * Devido a pequenas variações de largura de colunas entre diferentes ERPs emissores (Totvs, Linx, Sankhya, SAP, etc.), o alinhamento das colunas de impostos do item (`B.CÁLC ICMS`, `VALOR ICMS`, `VALOR IPI`, `ALÍQ. ICMS`, `ALÍQ. IPI`) é calculado dinamicamente em relação aos centros e limites dos cabeçalhos de cada página.
4. **Descrições de Produtos Multilinhas:**
   * Linhas secundárias contendo referências, modelos ou números de catálogo são automaticamente agregadas à descrição do produto anterior sem quebra de integridade tabular.
5. **Detecção Automatizada de Menções a ICMS-ST:**
   * Leitura das `INFORMAÇÕES COMPLEMENTARES` com marcação booleana (`tem_mencao_icms_st`) e isolamento de referências legais (Decretos SEFIN/CRE de Rondônia, resoluções e convênios).

---

## 3. Esquema das Tabelas Geradas

A extração produz três arquivos relacionais integrados via `chave_acesso`:

### `nfe_documentos.csv` (1 registro por nota fiscal)
* `chave_acesso` (Chave primária, 44 dígitos)
* `numero_nf`, `serie`, `folha`, `tipo_operacao`, `natureza_operacao`, `protocolo_autorizacao`
* `data_emissao`, `data_saida`, `hora_saida`
* `emitente_cnpj`, `emitente_ie`, `emitente_ie_st`, `emitente_uf`
* `destinatario_cnpj_cpf`, `destinatario_ie`, `destinatario_uf`
* Totais: `bc_icms`, `valor_icms`, `bc_icms_st`, `valor_icms_st`, `valor_imp_importacao`, `valor_icms_uf_remet`, `valor_fcp_uf_dest`, `valor_pis`, `valor_total_produtos`, `valor_frete`, `valor_seguro`, `valor_desconto`, `outras_despesas`, `valor_total_ipi`, `valor_icms_uf_dest`, `valor_tot_trib`, `valor_cofins`, `valor_total_nota`
* `modalidade_frete`, `transportador_cnpj_cpf`, `placa_veiculo`
* `info_complementares`, `tem_mencao_icms_st`, `pagina_arquivo`, `arquivo_origem`

### `nfe_itens.csv` (1 registro por item de produto/serviço)
* `chave_acesso` (Chave estrangeira)
* `numero_item` (Sequencial 1..N)
* `codigo_produto`, `descricao`, `ncm`, `cst_csosn`, `tipo_tributacao`, `cfop`, `unidade`
* `quantidade`, `valor_unitario`, `valor_total`, `desconto`
* `bc_icms`, `valor_icms`, `valor_ipi`, `aliq_icms`, `aliq_ipi`
* `pagina_arquivo`

### `nfe_duplicatas.csv` (1 registro por parcela de pagamento)
* `chave_acesso` (Chave estrangeira)
* `numero_duplicata`, `data_vencimento`, `valor`, `pagina_arquivo`

---

## 4. Como Executar

### Pré-requisitos
* Python 3.10 ou superior
* Utilitário `pdftotext` (pacote `poppler-utils` no Linux)
  ```bash
  sudo apt-get install poppler-utils
  ```

### Execução via Linha de Comando (CLI)

```bash
# Execução processando arquivo PDF específico (saída padrão na pasta ./output)
python main.py -i "/caminho/para/danfe.pdf"

# Execução processando um diretório com múltiplos PDFs e salvando em pasta personalizada
python main.py -i "/caminho/para/pasta_pdfs" -o "/caminho/para/saida"

# Gerando somente arquivos CSV (sem gerar a planilha consolidada em .xlsx)
python main.py -i "/caminho/para/danfe.pdf" --no-excel
```

---

## 5. Política de Privacidade de Dados

Este projeto foi desenvolvido em estrita conformidade com diretrizes de privacidade:
* Nenhum dado pessoal (CPFs, nomes de pessoas físicas ou endereços residenciais) é armazenado no código fonte ou na documentação do projeto.
* Todos os dados extraídos são tratados de forma puramente computacional e gravados em diretório de saída com permissões de acesso locais.
