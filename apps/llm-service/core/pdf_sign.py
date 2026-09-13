"""Gera PDF assinado: carimbo na 1ª página + página de assinatura."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from datetime import datetime

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor


GOLD  = HexColor("#c9a84c")
GOLDL = HexColor("#e8cf82")
INK   = HexColor("#1c1c1c")
GREY  = HexColor("#6b6b6b")
LIGHT = HexColor("#f4f1ea")


def _stamp_primeira_pagina(w, h, dados: dict) -> BytesIO:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))

    # caixa do carimbo (canto inferior direito)
    box_w, box_h = 260, 88
    x = w - box_w - 24
    y = 24

    # fundo
    c.setFillColor(LIGHT)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.roundRect(x, y, box_w, box_h, 6, stroke=1, fill=1)

    # título
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 12, y + box_h - 18, "ASSINATURA DIGITAL · Para.AI")

    # dados
    c.setFont("Helvetica", 7)
    c.setFillColor(GREY)
    c.drawString(x + 12, y + box_h - 34, f"Tarefa: {dados['tarefa_hash'][:20]}…")
    c.drawString(x + 12, y + box_h - 46, f"Rodada: {dados['numero']} · Acertos: {dados['acertos']}/{dados['total']}")
    c.drawString(x + 12, y + box_h - 58, f"Data: {dados['ts'][:19]} UTC")
    c.setFont("Helvetica-Oblique", 6)
    c.setFillColor(GOLD)
    c.drawString(x + 12, y + 12, f"Hash: {dados['hash_imutavel'][:40]}…")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def _pagina_assinatura(dados: dict) -> BytesIO:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # cabeçalho dourado
    c.setFillColor(GOLD)
    c.rect(0, H - 70, W, 70, stroke=0, fill=1)

    c.setFillColor(HexColor("#0b0d14"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(48, H - 44, "Assinatura Digital")
    c.setFont("Helvetica", 11)
    c.drawString(48, H - 60, "Para.AI · AI Forensics · termo de ciência")

    # corpo
    y = H - 110
    c.setFillColor(INK)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(48, y, "Termo de ciência")
    y -= 22
    c.setFont("Helvetica", 10)
    texto = (
        "O(a) signatário(a) abaixo identificado(a) declara ter lido o resumo "
        "estruturado apresentado no link público desta tarefa, ter respondido "
        "ao questionário de verificação de compreensão, e ter atingido o "
        "critério mínimo de acertos estabelecido. O presente documento "
        "constitui prova digital inequívoca do consentimento informado."
    )
    for linha in _quebrar(texto, 88):
        c.drawString(48, y, linha); y -= 14

    # caixa de dados
    y -= 12
    c.setFillColor(LIGHT); c.setStrokeColor(GOLD); c.setLineWidth(1)
    box_h = 210
    c.roundRect(48, y - box_h, W - 96, box_h, 8, stroke=1, fill=1)

    y -= 26
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 11)
    c.drawString(64, y, "Identificação da tarefa"); y -= 18

    linhas = [
        ("Título",             dados.get("titulo", "—")),
        ("Tarefa (hash)",      dados.get("tarefa_hash", "—")),
        ("Rodada",             str(dados.get("numero", "—"))),
        ("Data da assinatura", dados.get("ts", "—")),
        ("Acertos",            f"{dados.get('acertos','?')}/{dados.get('total','?')}"),
        ("IP",                 dados.get("ip", "—")),
        ("Navegador",          (dados.get("user_agent") or "—")[:70]),
    ]
    c.setFont("Helvetica", 9)
    for rot, val in linhas:
        c.setFillColor(GREY); c.drawString(64, y, f"{rot}:")
        c.setFillColor(INK);  c.drawString(180, y, val)
        y -= 16

    # bloco do hash imutável
    y -= 8
    c.setFillColor(GREY); c.setFont("Helvetica-Bold", 9)
    c.drawString(64, y, "Hash imutável (SHA-256):")
    y -= 16
    c.setFillColor(HexColor("#0b0d14"))
    c.setFont("Courier-Bold", 8.5)
    for linha in _quebrar(dados["hash_imutavel"], 78):
        c.drawString(64, y, linha); y -= 12

    # rodapé
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(GREY)
    c.drawString(48, 40, "Documento gerado automaticamente. O hash acima é a impressão digital desta assinatura:")
    c.drawString(48, 30, "qualquer alteração de dados invalida sua verificação.")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def _quebrar(txt: str, n: int) -> list[str]:
    return [txt[i:i+n] for i in range(0, len(txt), n)]


def gerar_pdf_assinado(
    pdf_original: Path,
    pdf_saida: Path,
    dados: dict,
) -> Path:
    """Sobrepõe carimbo na 1ª página + adiciona página de assinatura."""
    reader = PdfReader(str(pdf_original))
    writer = PdfWriter()

    # 1) carimbo na primeira página
    p0 = reader.pages[0]
    w = float(p0.mediabox.width)
    h = float(p0.mediabox.height)
    stamp = PdfReader(_stamp_primeira_pagina(w, h, dados)).pages[0]
    p0.merge_page(stamp)
    writer.add_page(p0)

    # 2) demais páginas
    for p in reader.pages[1:]:
        writer.add_page(p)

    # 3) página de assinatura no fim
    sig = PdfReader(_pagina_assinatura(dados)).pages[0]
    writer.add_page(sig)

    pdf_saida.parent.mkdir(parents=True, exist_ok=True)
    with pdf_saida.open("wb") as f:
        writer.write(f)
    return pdf_saida