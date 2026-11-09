"""
Orquestrador central de extração de dados de notas fiscais eletrônicas em PDF.
Aplica princípios de Inversão de Controle / Injeção de Dependências (DIP)
e Logging Estruturado.
"""

import os
import time
import logging
from typing import List, Tuple, Optional

from schemas import NFeDocumento, NFeItem, NFeDuplicata
from pdf_engine import IPdfEngine, PopplerPdfEngine
from parser_sections import NFeSectionPipeline, _default_pipeline
from parser_items import ItemTableParser, _default_item_parser

logger = logging.getLogger("danfe_extractor")


class DanfeExtractor:
    """
    Coordenador de alto nível para processamento de arquivos e diretórios de DANFEs.
    Recebe motores e parsers injetados ou utiliza implementações padrão de alta performance.
    """

    def __init__(
        self,
        pdf_engine: Optional[IPdfEngine] = None,
        section_pipeline: Optional[NFeSectionPipeline] = None,
        item_parser: Optional[ItemTableParser] = None,
        verbose: bool = True
    ):
        self.pdf_engine = pdf_engine or PopplerPdfEngine()
        self.section_pipeline = section_pipeline or _default_pipeline
        self.item_parser = item_parser or _default_item_parser
        self.verbose = verbose

        # Configura o logger com nível apropriado
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        logger.setLevel(logging.INFO if verbose else logging.WARNING)

    def process_pdf(self, pdf_path: str) -> Tuple[List[NFeDocumento], List[NFeItem], List[NFeDuplicata]]:
        """
        Processa todas as páginas de um arquivo PDF e extrai documentos, itens e duplicatas.
        """
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

        file_name = os.path.basename(pdf_path)
        start_time = time.time()

        logger.info(f"Lendo páginas de {file_name}...")
        pages = self.pdf_engine.extract_pages(pdf_path)
        total_pages = len(pages)

        logger.info(f"Extraindo dados fiscais de {total_pages} páginas...")

        documentos: List[NFeDocumento] = []
        todos_itens: List[NFeItem] = []
        todas_duplicatas: List[NFeDuplicata] = []

        for p_idx, page_text in enumerate(pages, start=1):
            lines = page_text.splitlines()

            # Extração de seções do documento (cabeçalho, duplicatas e totais)
            doc, duplicatas = self.section_pipeline.parse_page(
                text=page_text,
                lines=lines,
                page_num=p_idx,
                file_name=file_name
            )

            if doc:
                documentos.append(doc)
                todas_duplicatas.extend(duplicatas)

                # Extração dos itens de produtos da página
                itens = self.item_parser.parse(
                    lines=lines,
                    chave_acesso=doc.chave_acesso,
                    page_num=p_idx
                )
                todos_itens.extend(itens)

            if self.verbose and (p_idx % 50 == 0 or p_idx == total_pages):
                elapsed = time.time() - start_time
                logger.info(
                    f"Progresso: {p_idx}/{total_pages} páginas "
                    f"({len(documentos)} NFs, {len(todos_itens)} itens) - {elapsed:.1f}s"
                )

        elapsed_total = time.time() - start_time
        logger.info(f"Concluído em {elapsed_total:.2f}s!")
        logger.info(f"  - Documentos extraídos: {len(documentos)}")
        logger.info(f"  - Itens de produto extraídos: {len(todos_itens)}")
        logger.info(f"  - Duplicatas/Faturas extraídas: {len(todas_duplicatas)}")

        return documentos, todos_itens, todas_duplicatas

    def process_directory(self, dir_path: str) -> Tuple[List[NFeDocumento], List[NFeItem], List[NFeDuplicata]]:
        """
        Processa todos os arquivos .pdf encontrados em um diretório.
        """
        if not os.path.isdir(dir_path):
            raise NotADirectoryError(f"Diretório não encontrado: {dir_path}")

        pdf_files = [
            os.path.join(dir_path, f)
            for f in sorted(os.listdir(dir_path))
            if f.lower().endswith('.pdf')
        ]

        if not pdf_files:
            logger.warning(f"Nenhum arquivo PDF encontrado em {dir_path}")
            return [], [], []

        logger.info(f"Encontrados {len(pdf_files)} arquivos PDF para processamento.")

        todos_docs: List[NFeDocumento] = []
        todos_itens: List[NFeItem] = []
        todas_dups: List[NFeDuplicata] = []

        for f in pdf_files:
            docs, itens, dups = self.process_pdf(f)
            todos_docs.extend(docs)
            todos_itens.extend(itens)
            todas_dups.extend(dups)

        return todos_docs, todos_itens, todas_dups
