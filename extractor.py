"""
Orquestrador central de extração de dados de notas fiscais eletrônicas em PDF.
"""

import os
import time
from typing import List, Tuple
from schemas import NFeDocumento, NFeItem, NFeDuplicata
from pdf_engine import extract_all_pages_text
from parser_sections import parse_document_header_and_totals
from parser_items import extract_items_from_page


class DanfeExtractor:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def process_pdf(self, pdf_path: str) -> Tuple[List[NFeDocumento], List[NFeItem], List[NFeDuplicata]]:
        """
        Processa todas as páginas de um arquivo PDF e extrai documentos, itens e duplicatas.
        """
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

        file_name = os.path.basename(pdf_path)
        start_time = time.time()

        if self.verbose:
            print(f"[DanfeExtractor] Lendo páginas de {file_name}...")

        pages = extract_all_pages_text(pdf_path)
        total_pages = len(pages)

        if self.verbose:
            print(f"[DanfeExtractor] Extraindo dados fiscais de {total_pages} páginas...")

        documentos: List[NFeDocumento] = []
        todos_itens: List[NFeItem] = []
        todas_duplicatas: List[NFeDuplicata] = []

        for p_idx, page_text in enumerate(pages, start=1):
            lines = page_text.splitlines()

            # Extração de cabeçalho, duplicatas e totais
            doc, duplicatas = parse_document_header_and_totals(
                text=page_text,
                lines=lines,
                page_num=p_idx,
                file_name=file_name
            )

            if doc:
                documentos.append(doc)
                todas_duplicatas.extend(duplicatas)

                # Extração dos itens da nota fiscal
                itens = extract_items_from_page(
                    lines=lines,
                    chave_acesso=doc.chave_acesso,
                    page_num=p_idx
                )
                todos_itens.extend(itens)

            if self.verbose and (p_idx % 50 == 0 or p_idx == total_pages):
                elapsed = time.time() - start_time
                print(f"  > Progresso: {p_idx}/{total_pages} páginas ({len(documentos)} NFs, {len(todos_itens)} itens) - {elapsed:.1f}s")

        elapsed_total = time.time() - start_time
        if self.verbose:
            print(f"[DanfeExtractor] Concluído em {elapsed_total:.2f}s!")
            print(f"  - Documentos extraídos: {len(documentos)}")
            print(f"  - Itens de produto extraídos: {len(todos_itens)}")
            print(f"  - Duplicatas/Faturas extraídas: {len(todas_duplicatas)}")

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
            print(f"[DanfeExtractor] Nenhum arquivo PDF encontrado em {dir_path}")
            return [], [], []

        print(f"[DanfeExtractor] Encontrados {len(pdf_files)} arquivos PDF para processamento.")

        todos_docs: List[NFeDocumento] = []
        todos_itens: List[NFeItem] = []
        todas_dups: List[NFeDuplicata] = []

        for f in pdf_files:
            docs, itens, dups = self.process_pdf(f)
            todos_docs.extend(docs)
            todos_itens.extend(itens)
            todas_dups.extend(dups)

        return todos_docs, todos_itens, todas_dups
