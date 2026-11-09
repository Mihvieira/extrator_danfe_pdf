#!/usr/bin/env python3
"""
Ponto de entrada (CLI) do extrator de dados de DANFEs / Notas Fiscais Eletrônicas em PDF.
"""

import os
import sys
import argparse
from extractor import DanfeExtractor
from exporter import export_to_csv_and_excel


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extrator de dados de Notas Fiscais Eletrônicas (DANFE Modelo 55) em PDF."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Caminho do arquivo PDF ou pasta contendo PDFs a serem processados"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default="output",
        help="Diretório de destino para os arquivos CSV/Excel exportados (padrão: output)"
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Desativa a geração do arquivo consolidado .xlsx (gera apenas CSVs)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Modo silencioso, oculta logs parciais"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    input_path = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output_dir)

    if not os.path.exists(input_path):
        print(f"[ERRO] Caminho de entrada não existe: {input_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print(" EXTRATOR DE DADOS DE NOTAS FISCAIS ELETRÔNICAS (DANFE - MODELO 55)")
    print("=" * 70)
    print(f"Entrada : {input_path}")
    print(f"Destino : {output_dir}")
    print("=" * 70)

    extractor = DanfeExtractor(verbose=not args.quiet)

    if os.path.isdir(input_path):
        docs, itens, dups = extractor.process_directory(input_path)
    else:
        docs, itens, dups = extractor.process_pdf(input_path)

    if not docs:
        print("[AVISO] Nenhum documento válido foi extraído.", file=sys.stderr)
        sys.exit(1)

    print("\n[Exportador] Gravando arquivos de saída...")
    paths = export_to_csv_and_excel(
        documentos=docs,
        itens=itens,
        duplicatas=dups,
        output_dir=output_dir,
        export_excel=not args.no_excel
    )

    print("\n[Sucesso] Arquivos gerados com sucesso:")
    for k, p in paths.items():
        print(f"  - {k}: {p}")
    print("=" * 70)


if __name__ == "__main__":
    main()
