"""
Módulo de exportação dos dados estruturados para CSV e Excel.
"""

import os
from typing import List
import pandas as pd
from schemas import NFeDocumento, NFeItem, NFeDuplicata


def export_to_csv_and_excel(
    documentos: List[NFeDocumento],
    itens: List[NFeItem],
    duplicatas: List[NFeDuplicata],
    output_dir: str,
    export_excel: bool = True
) -> dict:
    """
    Exporta os objetos extraídos em tabelas relacionais em CSV e opcionalmente em Excel (.xlsx).
    """
    os.makedirs(output_dir, exist_ok=True)

    df_docs = pd.DataFrame([d.to_dict() for d in documentos])
    df_itens = pd.DataFrame([it.to_dict() for it in itens])
    df_dups = pd.DataFrame([dp.to_dict() for dp in duplicatas])

    docs_csv = os.path.join(output_dir, "nfe_documentos.csv")
    itens_csv = os.path.join(output_dir, "nfe_itens.csv")
    dups_csv = os.path.join(output_dir, "nfe_duplicatas.csv")

    df_docs.to_csv(docs_csv, index=False, sep=";", encoding="utf-8-sig")
    df_itens.to_csv(itens_csv, index=False, sep=";", encoding="utf-8-sig")
    df_dups.to_csv(dups_csv, index=False, sep=";", encoding="utf-8-sig")

    paths = {
        "documentos_csv": docs_csv,
        "itens_csv": itens_csv,
        "duplicatas_csv": dups_csv
    }

    if export_excel:
        excel_path = os.path.join(output_dir, "extracao_nfe_consolidada.xlsx")
        try:
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                df_docs.to_excel(writer, sheet_name="Documentos", index=False)
                df_itens.to_excel(writer, sheet_name="Itens", index=False)
                df_dups.to_excel(writer, sheet_name="Duplicatas", index=False)
            paths["excel"] = excel_path
        except Exception as e:
            # Se openpyxl não estiver instalado ou falhar, apenas reporta no log
            paths["excel_error"] = str(e)

    return paths
