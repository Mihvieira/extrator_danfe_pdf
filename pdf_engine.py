"""
Motor de extração de texto de PDF com preservação de layout posicional (A4).
Utiliza pdftotext (Poppler) nativo via subprocess, atingindo altíssima performance.
"""

import subprocess
import shutil
from typing import List, Generator, Tuple


def check_dependencies():
    """
    Verifica se a ferramenta pdftotext está disponível no sistema.
    """
    if not shutil.which("pdftotext"):
        raise RuntimeError(
            "pdftotext não foi encontrado no PATH do sistema. "
            "No Linux Ubuntu/Debian, instale com: sudo apt-get install poppler-utils"
        )


def extract_all_pages_text(pdf_path: str) -> List[str]:
    """
    Extrai o texto de todas as páginas de um arquivo PDF preservando o layout colunar.
    Retorna uma lista onde cada elemento é o texto de uma página.
    """
    check_dependencies()
    cmd = ["pdftotext", "-layout", pdf_path, "-"]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
    if res.returncode != 0:
        raise RuntimeError(f"Erro ao executar pdftotext no arquivo {pdf_path}: {res.stderr}")

    pages = res.stdout.split('\x0c')
    if pages and not pages[-1].strip():
        pages.pop()

    return pages


def iter_pages_text(pdf_path: str, start_page: int = 1, end_page: int = None) -> Generator[Tuple[int, str], None, None]:
    """
    Gera pares (número_da_página, texto) para as páginas especificadas.
    """
    pages = extract_all_pages_text(pdf_path)
    total = len(pages)
    end = min(end_page, total) if end_page else total

    for p_num in range(start_page, end + 1):
        yield p_num, pages[p_num - 1]
