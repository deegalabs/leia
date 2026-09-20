"""Extração de texto de PDF usando pypdf (pura Python, zero deps de sistema)."""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from core.pdf_visible import visible_text

# U+00AD soft hyphen, U+200B..U+200D zero width marks, U+2060 word joiner, U+FEFF byte order mark, the
# bidirectional overrides U+202A..U+202E and isolates U+2066..U+2069, plus the C0/C1 controls. Every one of
# them can sit inside a word without being drawn, which breaks the literal search that anchors the excerpt.
INVISIBLE_CHARS = re.compile(
    "[\u00ad\u200b-\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069"
    "\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]"
)


@dataclass(frozen=True)
class Extraction:
    """O texto que o documento mostra e a conta do que ficou de fora."""

    text: str
    hidden_text_chars: int
    hidden_text_runs: int
    invisible_chars: int


def extract(caminho_pdf: Path) -> Extraction:
    """Texto visível de todas as páginas com separador, mais a contagem do que foi descartado."""
    reader = PdfReader(str(caminho_pdf))
    partes = []
    hidden_chars = 0
    hidden_runs = 0
    for i, page in enumerate(reader.pages, 1):
        try:
            visivel = visible_text(page)
            txt = visivel.text
            hidden_chars += visivel.hidden_chars
            hidden_runs += visivel.hidden_runs
        except Exception as e:
            txt = f"[ERRO na página {i}: {e}]"
        partes.append(f"\n\n===== PÁGINA {i} =====\n\n{txt}")
    texto, invisiveis = _normalizar("".join(partes))
    return Extraction(texto, hidden_chars, hidden_runs, invisiveis)


def extract_text(caminho_pdf: Path) -> str:
    """Retorna texto concatenado de todas as páginas com separador."""
    return extract(caminho_pdf).text


def _normalizar(txt: str) -> tuple[str, int]:
    """Normaliza whitespace preservando estrutura de parágrafos e devolve quantos invisíveis saíram."""
    # normaliza quebras
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt, invisiveis = INVISIBLE_CHARS.subn("", txt)
    # colapsa 3+ \n em 2
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    # remove espaços no fim de linha
    txt = re.sub(r"[ \t]+\n", "\n", txt)
    return txt.strip(), invisiveis
