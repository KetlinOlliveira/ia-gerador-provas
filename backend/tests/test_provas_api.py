"""Fluxo completo pela API: envio do material, geração, acompanhamento, histórico e exportação.

O LLM é o dublê de `tests/falsos.py`; banco, RAG, orquestrador e rotas são os reais.
O TestClient executa as tarefas em segundo plano antes de devolver a resposta, então
a prova já está pronta (ou com falha) quando o POST retorna.
"""

import io
import json
from datetime import UTC, datetime, timedelta

import pytest
from docx import Document
from sqlalchemy import update

from app.db.modelos import Prova
from app.esquemas.provas import QuestaoDissertativa
from app.servicos.provas import MENSAGEM_INTERROMPIDA, marcar_provas_interrompidas

AULA = (
    "REST é um estilo arquitetural baseado em recursos identificados por URIs. "
    "Os métodos HTTP mais usados são GET, POST, PUT e DELETE. "
    "Uma API REST deve ser stateless, sem guardar sessão do cliente no servidor. "
    "Os códigos de status da faixa 4xx indicam erro do cliente, como 404 Not Found."
)


def enviar_material(cliente, nome="aula_rest-http.txt", texto=AULA):
    resposta = cliente.post("/api/v1/documentos", files={"arquivo": (nome, texto.encode())})
    assert resposta.status_code in (200, 201)
    return resposta.json()["id"]


def criar_prova(cliente, documento_id, titulo=None, dificuldade="medio", **quantidades):
    quantidades = quantidades or {"multipla_escolha": 2, "dissertativas": 1, "verdadeiro_falso": 1}
    corpo = {
        "documento_id": documento_id,
        "configuracao": {"dificuldade": dificuldade, **quantidades},
    }
    if titulo:
        corpo["titulo"] = titulo
    return cliente.post("/api/v1/provas", json=corpo)


def ler_eventos(texto):
    eventos = []
    for bloco in texto.strip().split("\n\n"):
        linhas = dict(linha.split(": ", 1) for linha in bloco.splitlines())
        eventos.append((linhas["event"], json.loads(linhas["data"])))
    return eventos


@pytest.fixture
def documento_id(cliente):
    return enviar_material(cliente)


# ---------- Criação e geração ----------


def test_cria_e_gera_a_prova_em_segundo_plano(cliente, documento_id):
    resposta = criar_prova(cliente, documento_id)

    assert resposta.status_code == 202
    criada = resposta.json()
    assert criada["titulo"] == "aula rest http"  # vem do nome do arquivo
    assert criada["total_questoes"] == 4

    prova = cliente.get(f"/api/v1/provas/{criada['id']}").json()
    assert prova["status"] == "concluida"
    assert prova["progresso"] == {
        "status": "concluida",
        "etapa": "geracao",
        "mensagem": "Prova pronta",
        "concluidas": 4,
        "total": 4,
        "erro": None,
    }
    assert [q["conteudo"]["tipo"] for q in prova["questoes"]] == [
        "multipla_escolha",
        "dissertativa",
        "verdadeiro_falso",
        "multipla_escolha",
    ]
    assert all(q["fontes"] and q["avaliacao"]["nota"] == 9 for q in prova["questoes"])
    assert len(prova["topicos"]) == 3
    assert prova["duracao_segundos"] is not None
    assert prova["concluido_em"] is not None


def test_usa_o_titulo_informado(cliente, documento_id):
    resposta = criar_prova(cliente, documento_id, titulo="  Prova bimestral  ")

    assert resposta.json()["titulo"] == "Prova bimestral"


def test_recusa_documento_inexistente_e_configuracao_vazia(cliente, documento_id):
    assert criar_prova(cliente, "nao-existe").status_code == 404

    vazia = criar_prova(cliente, documento_id, multipla_escolha=0)
    assert vazia.status_code == 422


def test_falha_do_llm_vira_status_com_mensagem(cliente, documento_id, llm_falso):
    llm_falso.falhar_em = QuestaoDissertativa

    criada = criar_prova(cliente, documento_id).json()

    prova = cliente.get(f"/api/v1/provas/{criada['id']}").json()
    assert prova["status"] == "falhou"
    assert prova["progresso"]["erro"] == "falhou"
    assert prova["questoes"] == []


# ---------- Acompanhamento (SSE) ----------


def test_eventos_terminam_com_a_prova_concluida(cliente, documento_id):
    criada = criar_prova(cliente, documento_id).json()

    resposta = cliente.get(f"/api/v1/provas/{criada['id']}/eventos")

    assert resposta.headers["content-type"].startswith("text/event-stream")
    eventos = ler_eventos(resposta.text)
    assert [nome for nome, _ in eventos] == ["progresso", "fim"]
    assert eventos[-1][1]["status"] == "concluida"
    assert eventos[-1][1]["concluidas"] == 4


def test_eventos_informam_a_falha(cliente, documento_id, llm_falso):
    llm_falso.falhar_em = QuestaoDissertativa
    criada = criar_prova(cliente, documento_id).json()

    _, dados = ler_eventos(cliente.get(f"/api/v1/provas/{criada['id']}/eventos").text)[-1]

    assert dados["status"] == "falhou"
    assert dados["erro"] == "falhou"


def test_eventos_de_prova_inexistente_devolvem_404(cliente):
    assert cliente.get("/api/v1/provas/nao-existe/eventos").status_code == 404


# ---------- Histórico ----------


def test_lista_com_busca_filtro_ordem_e_paginacao(cliente, documento_id):
    for titulo, dificuldade in [
        ("Redes - REST", "facil"),
        ("Redes - HTTP", "dificil"),
        ("Banco de dados", "facil"),
    ]:
        criar_prova(
            cliente, documento_id, titulo=titulo, dificuldade=dificuldade, multipla_escolha=1
        )

    def listar(**parametros):
        return cliente.get("/api/v1/provas", params=parametros).json()

    tudo = listar()
    assert tudo["total"] == 3
    assert [p["titulo"] for p in tudo["itens"]] == [
        "Banco de dados",
        "Redes - HTTP",
        "Redes - REST",
    ]

    assert [p["titulo"] for p in listar(ordem="antigas")["itens"]][0] == "Redes - REST"
    assert {p["titulo"] for p in listar(busca="redes")["itens"]} == {"Redes - REST", "Redes - HTTP"}
    assert [p["titulo"] for p in listar(dificuldade="dificil")["itens"]] == ["Redes - HTTP"]
    assert listar(busca="%")["total"] == 0  # curingas do LIKE são texto literal

    segunda = listar(por_pagina=2, pagina=2)
    assert segunda["total"] == 3
    assert [p["titulo"] for p in segunda["itens"]] == ["Redes - REST"]


def test_estatisticas_contam_o_total_e_o_mes(cliente, documento_id, fabrica_testes):
    for _ in range(3):
        criar_prova(cliente, documento_id, multipla_escolha=1)
    with fabrica_testes() as sessao:
        antiga = sessao.query(Prova).first()
        antiga.criado_em = datetime.now(UTC) - timedelta(days=62)
        sessao.commit()

    assert cliente.get("/api/v1/provas/estatisticas").json() == {"total": 3, "este_mes": 2}


def test_exclui_a_prova(cliente, documento_id):
    criada = criar_prova(cliente, documento_id).json()

    assert cliente.delete(f"/api/v1/provas/{criada['id']}").status_code == 204
    assert cliente.get(f"/api/v1/provas/{criada['id']}").status_code == 404
    assert cliente.delete(f"/api/v1/provas/{criada['id']}").status_code == 404


def test_excluir_o_material_mantem_a_prova_no_historico(cliente, documento_id):
    criada = criar_prova(cliente, documento_id).json()

    cliente.delete(f"/api/v1/documentos/{documento_id}")

    prova = cliente.get(f"/api/v1/provas/{criada['id']}").json()
    assert prova["status"] == "concluida"
    assert prova["documento_id"] is None


def test_provas_interrompidas_por_reinicio_viram_falha(cliente, documento_id, fabrica_testes):
    pronta = criar_prova(cliente, documento_id).json()
    presa = criar_prova(cliente, documento_id).json()
    with fabrica_testes() as sessao:
        sessao.execute(update(Prova).where(Prova.id == presa["id"]).values(status="gerando"))
        sessao.commit()

    assert marcar_provas_interrompidas(fabrica_testes) == 1

    assert cliente.get(f"/api/v1/provas/{presa['id']}").json()["progresso"]["erro"] == (
        MENSAGEM_INTERROMPIDA
    )
    assert cliente.get(f"/api/v1/provas/{pronta['id']}").json()["status"] == "concluida"


# ---------- Exportação ----------


def exportar(cliente, prova_id, formato, versao="aluno"):
    return cliente.get(
        f"/api/v1/provas/{prova_id}/exportar", params={"formato": formato, "versao": versao}
    )


def test_exporta_markdown_sem_gabarito_para_o_aluno(cliente, documento_id):
    prova_id = criar_prova(cliente, documento_id, titulo="Prova de Redes").json()["id"]

    aluno = exportar(cliente, prova_id, "md")
    professor = exportar(cliente, prova_id, "md", "professor")

    assert aluno.headers["content-disposition"].endswith("prova-de-redes.md")
    assert "## Questão 1 (Múltipla escolha)" in aluno.text
    assert "Pergunta 1?" in aluno.text
    assert "Resposta correta" not in aluno.text
    assert "Critérios de correção" not in aluno.text

    assert professor.headers["content-disposition"].endswith("prova-de-redes-gabarito.md")
    assert "Resposta correta: B" in professor.text
    assert "Critérios de correção" in professor.text
    assert "Nota do revisor: 9/10" in professor.text


def test_exporta_docx(cliente, documento_id):
    prova_id = criar_prova(cliente, documento_id).json()["id"]

    resposta = exportar(cliente, prova_id, "docx", "professor")

    assert resposta.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml"
    )
    texto = "\n".join(p.text for p in Document(io.BytesIO(resposta.content)).paragraphs)
    assert "Resposta correta: B" in texto
    assert "(V) Afirmativa" in texto


def test_exporta_pdf_mesmo_com_caracteres_fora_do_latin1(cliente, documento_id):
    titulo = "Arquitetura cliente‑servidor “REST” — revisão"
    prova_id = criar_prova(cliente, documento_id, titulo=titulo).json()["id"]

    for versao in ("aluno", "professor"):
        resposta = exportar(cliente, prova_id, "pdf", versao)
        assert resposta.status_code == 200
        assert resposta.headers["content-type"] == "application/pdf"
        assert resposta.content.startswith(b"%PDF")


def test_nao_exporta_prova_que_nao_foi_concluida(cliente, documento_id, llm_falso):
    llm_falso.falhar_em = QuestaoDissertativa
    prova_id = criar_prova(cliente, documento_id).json()["id"]

    resposta = exportar(cliente, prova_id, "pdf")

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "conflito"
