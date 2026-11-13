"""
Funções utilitárias de limpeza e conversão de tipos de dados para DANFEs.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional


def parse_decimal(value: Optional[str], default: Optional[Decimal] = Decimal("0.00")) -> Optional[Decimal]:
    """
    Converte número formatado no padrão brasileiro (ex: '1.234,56' ou '123,45') para Decimal.
    Trata strings vazias ou nulas retornando o valor default.
    """
    if not value:
        return default
    text = value.strip()
    if not text:
        return default

    # Remove símbolos de moeda ou espaços
    text = re.sub(r'[^\d,.-]', '', text)
    if not text:
        return default

    # Substitui separador de milhar e decimal
    # Se houver ponto e vírgula (ex: 1.234,56), remove o ponto e troca vírgula por ponto
    if '.' in text and ',' in text:
        text = text.replace('.', '').replace(',', '.')
    elif ',' in text:
        text = text.replace(',', '.')

    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return default


def parse_date_br(date_str: Optional[str]) -> Optional[str]:
    """
    Converte data de formato DD/MM/AAAA para formato ISO AAAA-MM-DD.
    """
    if not date_str:
        return None
    m = re.search(r'\b(\d{2})/(\d{2})/(\d{4})\b', date_str.strip())
    if m:
        day, month, year = m.groups()
        return f"{year}-{month}-{day}"
    return None


def clean_spaces(text: Optional[str]) -> str:
    """
    Remove quebras de linha espúrias e normaliza múltiplos espaços em branco.
    """
    if not text:
        return ""
    return " ".join(text.split()).strip()
