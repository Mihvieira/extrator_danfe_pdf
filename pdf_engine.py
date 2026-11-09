"""
Motor de extração de texto de PDF com preservação de layout posicional (A4).
Utiliza o padrão Adapter / Protocol para desacoplar a ferramenta subjacente (Poppler pdftotext)
do restante do sistema, facilitando testes e extensões futuras.
"""

import subprocess
import shutil
from typing import List, Generator, Tuple, Protocol, Optional


class IPdfEngine(Protocol):
    """Contrato abstrato para motores de extração de texto em PDF."""

    def extract_pages(self, pdf_path: str) -> List[str]:
        """Extrai o texto estruturado de cada página do arquivo PDF."""
        ...


class PopplerPdfEngine:
    """
    Implementação de alta performance baseada no utilitário 'pdftotext' da suite Poppler.
    Preserva a fidelidade espacial com o modo '-layout'.
    """

    def __init__(self):
        self._ensure_dependencies()

    @staticmethod
    def _ensure_dependencies() -> None:
        if not shutil.which("pdftotext"):
            raise RuntimeError(
                "pdftotext não foi encontrado no PATH do sistema. "
                "No Linux Ubuntu/Debian, instale com: sudo apt-get install poppler-utils"
            )

    def extract_pages(self, pdf_path: str) -> List[str]:
        cmd = ["pdftotext", "-layout", pdf_path, "-"]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="ignore"
        )
        if res.returncode != 0:
            raise RuntimeError(f"Erro ao executar pdftotext no arquivo {pdf_path}: {res.stderr}")

        # O separador de quebra de página padrão do pdftotext é Form Feed (\x0c)
        pages = res.stdout.split('\x0c')
        if pages and not pages[-1].strip():
            pages.pop()

        return pages


# Instância padrão para conveniência
_default_engine = PopplerPdfEngine()


def check_dependencies() -> None:
    """Verifica se a ferramenta pdftotext está disponível no sistema."""
    PopplerPdfEngine._ensure_dependencies()


def extract_all_pages_text(pdf_path: str) -> List[str]:
    """
    Função de conveniência mantida para total compatibilidade.
    Extrai o texto de todas as páginas preservando o layout colunar.
    """
    return _default_engine.extract_pages(pdf_path)


def iter_pages_text(
    pdf_path: str,
    start_page: int = 1,
    end_page: Optional[int] = None
) -> Generator[Tuple[int, str], None, None]:
    """Gera pares (número_da_página, texto) para as páginas especificadas."""
    pages = extract_all_pages_text(pdf_path)
    total = len(pages)
    end = min(end_page, total) if end_page else total

    for p_num in range(start_page, end + 1):
        yield p_num, pages[p_num - 1]
