"""Extração de texto de PDF usando pypdf (pura Python, zero deps de sistema)."""
from __future__ import annotations
import re
from pathlib import Path
from pypdf import PdfReader


def extrair_texto(caminho_pdf: Path) -> str:
    """Retorna texto concatenado de todas as páginas com separador."""
    reader = PdfReader(str(caminho_pdf))
    partes = []
    for i, page in enumerate(reader.pages, 1):
        try:
            txt = page.extract_text() or ""
        except Exception as e:
            txt = f"[ERRO na página {i}: {e}]"
        partes.append(f"\n\n===== PÁGINA {i} =====\n\n{txt}")
    bruto = "".join(partes)
    return _normalizar(bruto)


def _normalizar(txt: str) -> str:
    """Normaliza whitespace preservando estrutura de parágrafos."""
    # normaliza quebras
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    # colapsa 3+ \n em 2
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    # remove espaços no fim de linha
    txt = re.sub(r"[ \t]+\n", "\n", txt)
    return txt.strip()