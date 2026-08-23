"""Gera os PDFs do acervo a partir das fontes em Markdown.

O acervo e distribuido e indexado em PDF, formato uniforme para todos os
documentos. As fontes ficam em `_fontes/`, em Markdown: e o que se revisa,
se compara em diff e se corrige. A pasta comeca com sublinhado, o que a
mantem fora da indexacao — indexar fonte e PDF duplicaria cada trecho.

    python scripts/gerar_pdfs.py              # regera tudo
    python scripts/gerar_pdfs.py --conferir   # so verifica se estao em dia

O renderizador cobre o subconjunto de Markdown usado nos documentos:
titulos, paragrafos, listas, tabelas, blocos de codigo, citacoes, regras
horizontais e as marcacoes de negrito e codigo em linha.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from agente_carros.config import carregar_configuracao  # noqa: E402

TINTA = colors.HexColor("#1a1a1a")
SUAVE = colors.HexColor("#5b6472")
DESTAQUE = colors.HexColor("#8a5a00")
LINHA = colors.HexColor("#d5d9e0")
FUNDO_CODIGO = colors.HexColor("#f4f5f7")


def estilos() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    comum = {"fontName": "Helvetica", "textColor": TINTA, "leading": 14}
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=20, leading=25, textColor=TINTA, spaceAfter=4, alignment=0,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", fontName="Helvetica", fontSize=9.5, leading=14,
            textColor=SUAVE, spaceAfter=2,
        ),
        "h1": ParagraphStyle(
            "h1", fontName="Helvetica-Bold", fontSize=14.5, leading=19,
            textColor=TINTA, spaceBefore=18, spaceAfter=7,
        ),
        "h2": ParagraphStyle(
            "h2", fontName="Helvetica-Bold", fontSize=12, leading=16,
            textColor=TINTA, spaceBefore=13, spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14,
            textColor=DESTAQUE, spaceBefore=10, spaceAfter=4,
        ),
        "corpo": ParagraphStyle(
            "corpo", **comum, fontSize=9.8, alignment=TA_JUSTIFY, spaceAfter=7,
        ),
        "item": ParagraphStyle("item", **comum, fontSize=9.8, spaceAfter=2),
        "citacao": ParagraphStyle(
            "citacao", fontName="Helvetica-Oblique", fontSize=9.5, leading=14,
            textColor=SUAVE, leftIndent=12, spaceBefore=4, spaceAfter=8,
            borderPadding=(0, 0, 0, 8),
        ),
        "codigo": ParagraphStyle(
            "codigo", fontName="Courier", fontSize=7.6, leading=10,
            textColor=TINTA, spaceAfter=2,
        ),
        "celula": ParagraphStyle(
            "celula", fontName="Helvetica", fontSize=8.4, leading=11, textColor=TINTA,
        ),
        "celula_cab": ParagraphStyle(
            "celula_cab", fontName="Helvetica-Bold", fontSize=8.4, leading=11,
            textColor=TINTA,
        ),
    }


def em_linha(texto: str) -> str:
    """Converte as marcacoes de linha para as tags que o reportlab entende."""
    texto = html.escape(texto, quote=False)
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)          # links: so o rotulo
    texto = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"<i>\1</i>", texto)
    texto = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8.6">\1</font>', texto)
    return texto


def montar_tabela(linhas: list[list[str]], est: dict, largura: float) -> Table:
    cabecalho = [Paragraph(em_linha(c), est["celula_cab"]) for c in linhas[0]]
    corpo = [[Paragraph(em_linha(c), est["celula"]) for c in linha] for linha in linhas[1:]]
    colunas = len(linhas[0])

    # A primeira coluna costuma ser o rotulo e merece mais espaco; as demais
    # dividem o que sobra por igual.
    if colunas > 1:
        primeira = largura * (0.38 if colunas <= 3 else 0.30)
        resto = (largura - primeira) / (colunas - 1)
        larguras = [primeira] + [resto] * (colunas - 1)
    else:
        larguras = [largura]

    tabela = Table([cabecalho] + corpo, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FUNDO_CODIGO),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, LINHA),
        ("GRID", (0, 0), (-1, -1), 0.3, LINHA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabela


def converter(markdown: str, est: dict, largura: float) -> list:
    """Traduz o Markdown para a lista de elementos do reportlab."""
    elementos: list = []
    linhas = markdown.splitlines()
    i = 0
    primeiro_titulo = True

    while i < len(linhas):
        linha = linhas[i]

        # bloco de codigo
        if linha.startswith("```"):
            i += 1
            bloco = []
            while i < len(linhas) and not linhas[i].startswith("```"):
                bloco.append(linhas[i])
                i += 1
            i += 1
            texto = "<br/>".join(
                html.escape(b, quote=False).replace(" ", "&nbsp;") for b in bloco
            )
            caixa = Table(
                [[Paragraph(texto, est["codigo"])]], colWidths=[largura], hAlign="LEFT"
            )
            caixa.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), FUNDO_CODIGO),
                ("BOX", (0, 0), (-1, -1), 0.3, LINHA),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            elementos += [caixa, Spacer(1, 9)]
            continue

        # tabela
        if linha.startswith("|") and i + 1 < len(linhas) and set(linhas[i + 1]) <= set("|-: "):
            bruto = []
            while i < len(linhas) and linhas[i].startswith("|"):
                bruto.append([c.strip() for c in linhas[i].strip().strip("|").split("|")])
                i += 1
            del bruto[1]
            elementos += [montar_tabela(bruto, est, largura), Spacer(1, 10)]
            continue

        # regra horizontal
        if linha.strip() == "---":
            elementos += [Spacer(1, 4), HRFlowable(width="100%", color=LINHA), Spacer(1, 8)]
            i += 1
            continue

        # titulos
        if linha.startswith("#"):
            nivel = len(linha) - len(linha.lstrip("#"))
            texto = linha.lstrip("#").strip()
            if nivel == 1 and primeiro_titulo:
                elementos.append(Paragraph(em_linha(texto), est["titulo"]))
                primeiro_titulo = False
            else:
                chave = {1: "h1", 2: "h1", 3: "h2"}.get(nivel, "h3")
                elementos.append(Paragraph(em_linha(texto), est[chave]))
            i += 1
            continue

        # citacao
        if linha.startswith(">"):
            bloco = []
            while i < len(linhas) and linhas[i].startswith(">"):
                bloco.append(linhas[i].lstrip(">").strip())
                i += 1
            elementos.append(Paragraph(em_linha(" ".join(bloco)), est["citacao"]))
            continue

        # listas
        marcador = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", linha)
        if marcador:
            numerada = bool(re.match(r"^\d+\.$", marcador.group(2)))
            itens = []
            while i < len(linhas):
                m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", linhas[i])
                if not m:
                    if linhas[i].strip() and linhas[i].startswith(("  ", "\t")) and itens:
                        itens[-1] += " " + linhas[i].strip()
                        i += 1
                        continue
                    break
                itens.append(m.group(3))
                i += 1
            elementos.append(ListFlowable(
                [ListItem(Paragraph(em_linha(t), est["item"]), leftIndent=14) for t in itens],
                bulletType="1" if numerada else "bullet",
                bulletFontSize=8, leftIndent=16, spaceAfter=8,
            ))
            continue

        # paragrafo
        if linha.strip():
            bloco = []
            while i < len(linhas) and linhas[i].strip() and not linhas[i].startswith(
                ("#", "|", ">", "```", "---")
            ):
                if re.match(r"^(\s*)([-*]|\d+\.)\s+", linhas[i]):
                    break
                bloco.append(linhas[i].strip())
                i += 1
            texto = " ".join(bloco)
            estilo = "subtitulo" if texto.startswith("**") and ":**" in texto else "corpo"
            elementos.append(Paragraph(em_linha(texto), est[estilo]))
            continue

        i += 1

    return elementos


def rodape(titulo: str):
    def desenhar(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(SUAVE)
        canvas.drawString(2.2 * cm, 1.3 * cm, titulo)
        canvas.drawRightString(A4[0] - 2.2 * cm, 1.3 * cm, f"Página {canvas.getPageNumber()}")
        canvas.setStrokeColor(LINHA)
        canvas.line(2.2 * cm, 1.7 * cm, A4[0] - 2.2 * cm, 1.7 * cm)
        canvas.restoreState()
    return desenhar


def gerar(origem: Path, destino: Path) -> int:
    """Escreve o PDF e devolve o numero de paginas."""
    est = estilos()
    markdown = origem.read_text(encoding="utf-8")
    # O titulo do documento vira o titulo do PDF: e o que aparece na aba do
    # leitor e nas propriedades do arquivo, e o nome do arquivo nao serve.
    titulo = next(
        (linha.lstrip("#").strip() for linha in markdown.splitlines() if linha.startswith("# ")),
        origem.stem,
    )
    documento = SimpleDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2.0 * cm, bottomMargin=2.2 * cm,
        title=titulo, author="Autoluz Veículos", subject="Documento interno",
    )
    largura = documento.width
    elementos = converter(markdown, est, largura)
    documento.build(elementos, onFirstPage=rodape(titulo), onLaterPages=rodape(titulo))

    from pypdf import PdfReader
    return len(PdfReader(str(destino)).pages)


def assinatura(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()[:16]


def main() -> None:
    analisador = argparse.ArgumentParser(description="Gera os PDFs do acervo")
    analisador.add_argument(
        "--conferir", action="store_true", help="Verifica se os PDFs estao em dia"
    )
    argumentos = analisador.parse_args()

    acervo = carregar_configuracao().caminhos.corporativos
    fontes = sorted((acervo / "_fontes").glob("*.md"))
    if not fontes:
        raise SystemExit(f"Nenhuma fonte em {acervo / '_fontes'}")

    # O manual do sistema documenta o projeto, nao a empresa. Sai em PDF
    # pelo mesmo renderizador, mas fica em docs/ e nao entra no indice: o
    # agente responde sobre carros e politicas, nao sobre a propria
    # implementacao.
    manual_md = RAIZ / "docs" / "MANUAL_DO_SISTEMA.md"
    manual_pdf = RAIZ / "docs" / "Manual_do_Sistema.pdf"

    controle = acervo / "_fontes" / ".assinaturas.json"
    anteriores = json.loads(controle.read_text()) if controle.exists() else {}
    atuais, desatualizados = {}, []

    for fonte in fontes:
        atuais[fonte.name] = assinatura(fonte)
        pdf = acervo / f"{fonte.stem}.pdf"
        if not pdf.exists() or anteriores.get(fonte.name) != atuais[fonte.name]:
            desatualizados.append(fonte)

    if argumentos.conferir:
        if not manual_pdf.exists():
            desatualizados.append(manual_md)
        if desatualizados:
            print("PDFs desatualizados:")
            for f in desatualizados:
                print(f"  {f.name}")
            raise SystemExit(1)
        print(f"{len(fontes)} PDFs em dia.")
        return

    print("Acervo corporativo:")
    total = 0
    for fonte in fontes:
        pdf = acervo / f"{fonte.stem}.pdf"
        paginas = gerar(fonte, pdf)
        total += paginas
        print(f"  {pdf.name:44} {paginas:>3} páginas")

    controle.write_text(json.dumps(atuais, indent=2), encoding="utf-8")
    print(f"  {len(fontes)} documentos, {total} páginas.")

    if manual_md.exists():
        print("\nDocumentação do projeto:")
        paginas = gerar(manual_md, manual_pdf)
        print(f"  {manual_pdf.name:44} {paginas:>3} páginas")


if __name__ == "__main__":
    main()
