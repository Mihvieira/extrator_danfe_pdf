# Extrator de Dados de Notas Fiscais Eletrônicas (DANFE Modelo 55)

Módulo em Python projetado para extração, validação e estruturação automatizada de dados fiscais a partir de Documentos Auxiliares da Nota Fiscal Eletrônica (DANFE) em formato PDF, com tratamento posicional e suporte às variações de leiaute do padrão nacional (Layout 4.00 e notas técnicas vigentes).

---

## 1. Visão Geral da Arquitetura

O extrator utiliza o utilitário nativo de alta performance `pdftotext` (Poppler) em modo colunar (`-layout`), processando centenas de páginas em poucos segundos sem necessidade de OCR ou dependências binárias complexas.

A arquitetura adota princípios de **Clean Code**, **Domain-Driven Design (DDD)** e **SOLID**:
- **Pipeline e Strategy Pattern**: Seções do DANFE são analisadas por parsers especializados e desacoplados (`NFeSectionPipeline`, `IdentificacaoParser`, `TotaisImpostoParser`, etc.).
- **Dependency Inversion (DIP)**: O motor de PDF é desacoplado através do protocolo `IPdfEngine`, facilitando extensões e testes unitários com mocks.
- **Value Objects Imutáveis**: Modelagem orientada a domínio em `schemas.py` com dataclasses imutáveis para integridade de dados fiscais.
- **Resiliência e Independência**: A exportação para CSV utiliza exclusivamente a biblioteca padrão do Python (`csv`), tornando as bibliotecas `pandas` e `openpyxl` estritamente opcionais para geração de planilhas Excel (`.xlsx`).

### Estrutura do Módulo

```
extrator_danfe_pdf/
├── README.md               # Documentação técnica e guia de execução
├── requirements.txt        # Dependências opcionais (pandas, openpyxl para Excel)
├── schemas.py              # Modelagem de domínio (NFeDocumento, NFeItem, NFeDuplicata, etc.)
├── utils.py                # Sanitização de strings e conversão monetária/decimal (PT-BR)
├── pdf_engine.py           # Interface IPdfEngine e motor PopplerPdfEngine
├── parser_sections.py      # Pipeline com parsers modulares de seções e impostos
├── parser_items.py         # ItemTableParser para extração tabular com suporte a multilinhas
├── extractor.py            # Orquestrador DanfeExtractor com logging estruturado e injeção
├── exporter.py             # Exportador de dados para CSV nativo e Excel (.xlsx)
├── main.py                 # Ponto de entrada CLI e execução direta por IDE
└── tests/                  # Suíte de testes unitários e de integração
    ├── test_extraction.py
    └── test_unit_parsers.py
```

---

## 2. Tratamento das Variações de Leiaute e Emissão

1. **Regime Normal (CST) vs. Simples Nacional (CSOSN):**
   * O parser detecta dinamicamente se o cabeçalho tabular contém a coluna `O/CST` (3 dígitos: origem + tributação) ou `O/CSOSN` (4 dígitos: origem + operação no Simples Nacional), preenchendo adequadamente o campo `tipo_tributacao`.
2. **Campos Estendidos de Imposto (EC 87/2015 & NT 2015.003 / 2016.002):**
   * Suporte às colunas de Partilha do ICMS interestadual (`V. ICMS UF REMET.`, `V. ICMS UF DEST.`, `V. FCP UF DEST.`), além de `V. TOT. TRIB.` (Lei 12.741/2012).
3. **Mapeamento Posicional por Proximidade:**
   * Devido a variações de largura de colunas entre diferentes emissores (Totvs, Linx, Sankhya, SAP, etc.), o alinhamento das colunas de tributos do item (`B.CÁLC ICMS`, `VALOR ICMS`, `VALOR IPI`, `ALÍQ. ICMS`, `ALÍQ. IPI`, `DESCONTO`) é calculado dinamicamente em relação aos centros e limites horizontais dos cabeçalhos.
4. **Descrições de Produtos Multilinhas:**
   * Linhas secundárias contendo referências, modelos ou números de catálogo são automaticamente concatenadas à descrição do produto anterior sem corromper a integridade tabular.
5. **Detecção Automatizada de Menções a ICMS-ST:**
   * Leitura e busca de padrões em `INFORMAÇÕES COMPLEMENTARES` com marcação booleana (`tem_mencao_icms_st`), isolando referências legais e decretos tributários.
6. **Transporte e Dados de Carga:**
   * Captura detalhada de modalidade de frete, transportador (CNPJ/CPF, UF), placa do veículo, quantidade de volumes e pesos (líquido e bruto).

---

## 3. Esquema das Tabelas Geradas

A extração produz três arquivos relacionais integrados via `chave_acesso`:

### `nfe_documentos.csv` (1 registro por nota fiscal)
* **Identificação:** `chave_acesso` (Chave primária, 44 dígitos), `numero_nf`, `serie`, `folha`, `tipo_operacao`, `natureza_operacao`, `protocolo_autorizacao`
* **Emitente:** `emitente_cnpj`, `emitente_ie`, `emitente_ie_st`, `emitente_uf`
* **Destinatário:** `destinatario_cnpj_cpf`, `destinatario_ie`, `destinatario_uf`, `data_emissao`, `data_saida`, `hora_saida`
* **Totais e Impostos:** `bc_icms`, `valor_icms`, `bc_icms_st`, `valor_icms_st`, `valor_imp_importacao`, `valor_icms_uf_remet`, `valor_fcp_uf_dest`, `valor_pis`, `valor_total_produtos`, `valor_frete`, `valor_seguro`, `valor_desconto`, `outras_despesas`, `valor_total_ipi`, `valor_icms_uf_dest`, `valor_tot_trib`, `valor_cofins`, `valor_total_nota`
* **Transporte e Carga:** `modalidade_frete`, `transportador_cnpj_cpf`, `transportador_uf`, `placa_veiculo`, `volume_quantidade`, `peso_bruto`, `peso_liquido`
* **Metadados:** `info_complementares`, `tem_mencao_icms_st`, `pagina_arquivo`, `arquivo_origem`

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
* **Python 3.10** ou superior
* Utilitário `pdftotext` (pacote `poppler-utils` no Linux)
  ```bash
  sudo apt-get install poppler-utils
  ```
* *(Opcional)* Dependências para exportação em Excel (`.xlsx`):
  ```bash
  pip install -r requirements.txt
  ```

---

### Modos de Execução

#### Opção A: Execução Direta / IDE (F5 ou Botão Run)
Para executar diretamente pela IDE ou digitando `python3 main.py` sem passar argumentos de linha de comando, basta configurar as constantes no início do arquivo `main.py`:

```python
# main.py
DEFAULT_INPUT_PATH = "/caminho/para/seus/arquivos_ou_pasta"
DEFAULT_OUTPUT_DIR = "output"
```

#### Opção B: Interface de Linha de Comando (CLI)

```bash
# Processando um único arquivo PDF (saída padrão na pasta ./output)
python3 main.py -i "/caminho/para/danfe.pdf"

# Processando uma pasta com múltiplos PDFs e salvando em pasta personalizada
python3 main.py -i "/caminho/para/pasta_danfes" -o "/caminho/para/saida"

# Gerando exclusivamente arquivos CSV (desativa geração do consolidado em .xlsx)
python3 main.py -i "/caminho/para/danfe.pdf" --no-excel

# Modo silencioso (oculta logs parciais de progresso)
python3 main.py -i "/caminho/para/pasta_danfes" -q
```

---

## 5. Testes Automatizados

O projeto possui uma suíte de testes automatizados com dados sintéticos mockados, garantindo isolamento completo e conformidade com a LGPD para execução em qualquer ambiente ou esteira de CI/CD (GitHub Actions):

```bash
# Execução da suíte padrão de testes unitários e de integração sintética:
python3 -m unittest discover tests

# (Opcional) Execução local com lote próprio de PDFs reais via variável de ambiente:
DANFE_REAL_PDF_PATH="/caminho/para/seu/arquivo.pdf" python3 -m unittest discover tests
```