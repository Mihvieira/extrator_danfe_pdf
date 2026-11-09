"""
Módulo de exportação dos dados estruturados para CSV e Excel.
Utiliza a biblioteca padrão 'csv' para máxima performance e independência de dependências,
com suporte opcional a pandas e openpyxl para exportação consolidada em Excel (.xlsx).
"""

import os
import csv
from typing import List, Dict, Any, Optional
from schemas import NFeDocumento, NFeItem, NFeDuplicata

# Importação opcional e segura de pandas/openpyxl
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pd = None
    HAS_PANDAS = False


def _write_csv(file_path: str, rows: List[Dict[str, Any]]) -> None:
    """Grava lista de dicionários em arquivo CSV formatado com ';' e encoding UTF-8 com BOM."""
    if not rows:
        # Se vazio, cria arquivo vazio
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            pass
        return

    fieldnames = list(rows[0].keys())
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_to_csv_and_excel(
    documentos: List[NFeDocumento],
    itens: List[NFeItem],
    duplicatas: List[NFeDuplicata],
    output_dir: str,
    export_excel: bool = True
) -> Dict[str, str]:
    """
    Exporta os objetos extraídos em tabelas relacionais em CSV e opcionalmente em Excel (.xlsx).
    """
    os.makedirs(output_dir, exist_ok=True)

    docs_dict = [d.to_dict() for d in documentos]
    itens_dict = [it.to_dict() for it in itens]
    dups_dict = [dp.to_dict() for dp in duplicatas]

    docs_csv = os.path.join(output_dir, "nfe_documentos.csv")
    itens_csv = os.path.join(output_dir, "nfe_itens.csv")
    dups_csv = os.path.join(output_dir, "nfe_duplicatas.csv")

    _write_csv(docs_csv, docs_dict)
    _write_csv(itens_csv, itens_dict)
    _write_csv(dups_csv, dups_dict)

    paths: Dict[str, str] = {
        "documentos_csv": docs_csv,
        "itens_csv": itens_csv,
        "duplicatas_csv": dups_csv
    }

    if export_excel:
        excel_path = os.path.join(output_dir, "extracao_nfe_consolidada.xlsx")
        if HAS_PANDAS:
            try:
                with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                    pd.DataFrame(docs_dict).to_excel(writer, sheet_name="Documentos", index=False)
                    pd.DataFrame(itens_dict).to_excel(writer, sheet_name="Itens", index=False)
                    pd.DataFrame(dups_dict).to_excel(writer, sheet_name="Duplicatas", index=False)
                paths["excel"] = excel_path
            except Exception as e:
                paths["excel_error"] = str(e)
        else:
            paths["excel_skipped"] = "Biblioteca 'pandas' não instalada; apenas CSVs foram gerados."

    return paths
