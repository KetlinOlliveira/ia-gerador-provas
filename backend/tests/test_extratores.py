import pytest

from app.core.excecoes import ErroArquivoInvalido, ErroDocumentoSemTexto, ErroTipoNaoSuportado
from app.ingestao.extratores import extrair_texto, identificar_tipo
from tests.arquivos import criar_docx, criar_pdf


@pytest.mark.parametrize(
    ("nome", "tipo"),
    [("aula.txt", "txt"), ("Aula 01.PDF", "pdf"), ("resumo.final.docx", "docx")],
)
def test_identifica_o_tipo_pela_extensao(nome, tipo):
    assert identificar_tipo(nome) == tipo


@pytest.mark.parametrize("nome", ["planilha.xlsx", "antigo.doc", "sem_extensao", ""])
def test_recusa_tipos_nao_suportados(nome):
    with pytest.raises(ErroTipoNaoSuportado):
        identificar_tipo(nome)


def test_txt_em_utf8_com_bom():
    extraido = extrair_texto("﻿Autenticação e autorização".encode(), "txt")

    assert extraido.paginas == ["Autenticação e autorização"]
    assert extraido.paginado is False


def test_txt_em_cp1252():
    extraido = extrair_texto("Requisição ao servidor".encode("cp1252"), "txt")

    assert extraido.paginas == ["Requisição ao servidor"]


def test_normaliza_espacos_e_quebras_de_linha():
    extraido = extrair_texto(b"Linha  um\t aqui \r\n\r\n\r\n\r\nLinha dois", "txt")

    assert extraido.paginas == ["Linha um aqui\n\nLinha dois"]


def test_docx_inclui_paragrafos_e_tabelas():
    conteudo = criar_docx(["Códigos de status HTTP"], tabela=[["200", "OK"], ["404", "Not Found"]])
    extraido = extrair_texto(conteudo, "docx")

    assert "Códigos de status HTTP" in extraido.paginas[0]
    assert "404 | Not Found" in extraido.paginas[0]
    assert extraido.paginado is False


def test_pdf_devolve_uma_entrada_por_pagina():
    extraido = extrair_texto(criar_pdf(["Arquitetura REST", "Metodos HTTP"]), "pdf")

    assert extraido.paginas == ["Arquitetura REST", "Metodos HTTP"]
    assert extraido.paginado is True


@pytest.mark.parametrize("tipo", ["pdf", "docx"])
def test_arquivo_corrompido_vira_erro_claro(tipo):
    with pytest.raises(ErroArquivoInvalido):
        extrair_texto(b"isto nao e um arquivo valido", tipo)


def test_arquivo_sem_texto_vira_erro_claro():
    with pytest.raises(ErroDocumentoSemTexto):
        extrair_texto(b"  \n\n  ", "txt")
    with pytest.raises(ErroDocumentoSemTexto):
        extrair_texto(criar_pdf([""]), "pdf")
