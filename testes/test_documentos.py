"""Testes da leitura multiformato.

O que importa aqui nao e "o arquivo foi lido", e sim que o texto extraido
sobreviva ao fatiamento: cada linha de tabela precisa carregar o proprio
cabecalho, senao o trecho recuperado vira uma fileira de numeros sem
legenda e o modelo responde com dado orfao.
"""

from __future__ import annotations

import json

import pytest

from agente_carros import documentos


def test_csv_repete_o_cabecalho_em_cada_linha(tmp_path):
    arquivo = tmp_path / "precos.csv"
    arquivo.write_text("modelo,preco\nCorolla,145000\nOnix,85000\n", encoding="utf-8")

    texto = documentos.extrair_texto(arquivo)

    assert "modelo: Corolla | preco: 145000" in texto
    # A segunda linha tambem precisa se sustentar sozinha.
    assert "modelo: Onix | preco: 85000" in texto


def test_csv_com_ponto_e_virgula(tmp_path):
    arquivo = tmp_path / "precos.csv"
    arquivo.write_text("modelo;preco\nCorolla;145000\n", encoding="utf-8")
    assert "modelo: Corolla | preco: 145000" in documentos.extrair_texto(arquivo)


def test_json_preserva_o_caminho_ate_a_folha(tmp_path):
    arquivo = tmp_path / "beneficios.json"
    arquivo.write_text(
        json.dumps({"beneficios": {"vale_refeicao": {"valor": 40}}, "areas": ["RH", "TI"]}),
        encoding="utf-8",
    )

    texto = documentos.extrair_texto(arquivo)

    assert "beneficios.vale_refeicao.valor: 40" in texto
    assert "areas[0]: RH" in texto


def test_html_descarta_script_e_navegacao(tmp_path):
    pytest.importorskip("bs4")
    arquivo = tmp_path / "faq.html"
    arquivo.write_text(
        "<html><body><nav>Menu</nav><h1>Garantia</h1>"
        "<p>Tres anos.</p><script>rastrear()</script></body></html>",
        encoding="utf-8",
    )

    texto = documentos.extrair_texto(arquivo)

    assert "Garantia" in texto
    assert "Tres anos." in texto
    assert "rastrear" not in texto
    assert "Menu" not in texto


def test_markdown_e_lido_como_texto(tmp_path):
    arquivo = tmp_path / "politica.md"
    arquivo.write_text("# Politica\n\nReembolso em 30 dias.\n", encoding="utf-8")
    assert "Reembolso em 30 dias." in documentos.extrair_texto(arquivo)


def test_formato_desconhecido_e_recusado(tmp_path):
    arquivo = tmp_path / "imagem.png"
    arquivo.write_bytes(b"\x89PNG")
    with pytest.raises(ValueError, match="nao suportado"):
        documentos.extrair_texto(arquivo)


def test_reconhece_os_formatos_do_acervo(tmp_path):
    assert documentos.eh_suportado(tmp_path / "manual.pdf")
    assert documentos.eh_suportado(tmp_path / "politica.docx")
    assert documentos.eh_suportado(tmp_path / "tabela.xlsx")
    assert not documentos.eh_suportado(tmp_path / "foto.jpg")


def test_docx_extrai_paragrafos_e_tabelas(tmp_path):
    docx = pytest.importorskip("docx")

    caminho = tmp_path / "politica.docx"
    documento = docx.Document()
    documento.add_paragraph("Politica de reembolso")
    tabela = documento.add_table(rows=2, cols=2)
    tabela.cell(0, 0).text = "item"
    tabela.cell(0, 1).text = "limite"
    tabela.cell(1, 0).text = "almoco"
    tabela.cell(1, 1).text = "80"
    documento.save(str(caminho))

    texto = documentos.extrair_texto(caminho)

    assert "Politica de reembolso" in texto
    assert "item: almoco | limite: 80" in texto


def test_xlsx_vira_uma_frase_por_linha(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    caminho = tmp_path / "tabela.xlsx"
    livro = openpyxl.Workbook()
    planilha = livro.active
    planilha.title = "Precos"
    planilha.append(["modelo", "preco"])
    planilha.append(["Corolla", 145000])
    livro.save(str(caminho))

    texto = documentos.extrair_texto(caminho)

    assert "# Planilha: Precos" in texto
    assert "modelo: Corolla | preco: 145000" in texto


def test_pptx_inclui_as_notas_do_apresentador(tmp_path):
    pptx = pytest.importorskip("pptx")

    caminho = tmp_path / "pitch.pptx"
    apresentacao = pptx.Presentation()
    slide = apresentacao.slides.add_slide(apresentacao.slide_layouts[5])
    slide.shapes.title.text = "Resultados"
    slide.notes_slide.notes_text_frame.text = "Numeros do terceiro trimestre"
    apresentacao.save(str(caminho))

    texto = documentos.extrair_texto(caminho)

    assert "Resultados" in texto
    assert "Numeros do terceiro trimestre" in texto
