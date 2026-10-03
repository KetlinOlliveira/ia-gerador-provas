from collections import Counter

import pytest

from app.agentes.orquestrador import OrquestradorProva, distribuir_questoes
from app.agentes.planejador import amostrar_material
from app.core.config import Configuracoes
from app.core.excecoes import ErroSaidaLLM
from app.esquemas.provas import (
    ConfiguracaoProva,
    Fonte,
    QuestaoDissertativa,
    TipoQuestao,
    Topico,
)
from app.llm.cliente import PapelModelo
from tests.falsos import LLMFalso, avaliacao

FONTES = [Fonte(ordem=i, pagina=None, texto=f"Trecho {i} do material.") for i in range(5)]


async def recuperar_falso(consulta, k):
    return FONTES[:k]


def orquestrador(llm, **ajustes):
    configuracoes = Configuracoes(_env_file=None, **ajustes)
    return OrquestradorProva(llm, recuperar_falso, configuracoes)


async def gerar(llm, ao_progredir=None, **quantidades):
    configuracao = ConfiguracaoProva(dificuldade="medio", **quantidades)
    return await orquestrador(llm).gerar("doc-1", FONTES, configuracao, ao_progredir)


# ---------- Distribuição ----------


def topicos(n):
    return [Topico(titulo=f"T{i}", descricao="") for i in range(n)]


def test_distribuicao_respeita_as_quantidades_e_alterna_os_tipos():
    configuracao = ConfiguracaoProva(
        dificuldade="facil", multipla_escolha=3, dissertativas=1, verdadeiro_falso=2
    )
    itens = distribuir_questoes(configuracao, topicos(4))

    assert [item.numero for item in itens] == [1, 2, 3, 4, 5, 6]
    assert [item.tipo for item in itens] == [
        TipoQuestao.MULTIPLA_ESCOLHA,
        TipoQuestao.DISSERTATIVA,
        TipoQuestao.VERDADEIRO_FALSO,
        TipoQuestao.MULTIPLA_ESCOLHA,
        TipoQuestao.VERDADEIRO_FALSO,
        TipoQuestao.MULTIPLA_ESCOLHA,
    ]


def test_distribuicao_nao_prende_um_topico_a_um_unico_tipo():
    configuracao = ConfiguracaoProva(
        dificuldade="facil", multipla_escolha=2, dissertativas=2, verdadeiro_falso=2
    )
    itens = distribuir_questoes(configuracao, topicos(3))

    tipos_por_topico = {}
    for item in itens:
        tipos_por_topico.setdefault(item.topico.titulo, set()).add(item.tipo)
    assert all(len(tipos) == 2 for tipos in tipos_por_topico.values())
    assert Counter(item.topico.titulo for item in itens) == {"T0": 2, "T1": 2, "T2": 2}


def test_amostra_cobre_o_documento_inteiro_dentro_do_limite():
    trechos = [Fonte(ordem=i, pagina=None, texto="x" * 100) for i in range(100)]

    amostra = amostrar_material(trechos, max_caracteres=1000)

    assert sum(len(trecho.texto) for trecho in amostra) <= 1000
    assert amostra[0].ordem == 0
    assert amostra[-1].ordem >= 90
    assert amostrar_material(trechos[:5], max_caracteres=1000) == trechos[:5]


# ---------- Geração ----------


async def test_gera_a_prova_completa_na_ordem_planejada():
    llm = LLMFalso()
    prova = await gerar(llm, multipla_escolha=2, dissertativas=2, verdadeiro_falso=2)

    assert [questao.numero for questao in prova.questoes] == [1, 2, 3, 4, 5, 6]
    assert [questao.conteudo.tipo for questao in prova.questoes] == [
        "multipla_escolha",
        "dissertativa",
        "verdadeiro_falso",
    ] * 2
    assert all(questao.aprovada and questao.tentativas == 1 for questao in prova.questoes)
    assert len(llm.chamadas_de(PapelModelo.PLANEJADOR)) == 1
    assert len(llm.chamadas_de(PapelModelo.GERADOR)) == 6
    assert len(llm.chamadas_de(PapelModelo.REVISOR)) == 6


async def test_gerador_recebe_os_trechos_recuperados_e_o_que_ja_foi_cobrado():
    llm = LLMFalso(topicos=1)
    await gerar(llm, multipla_escolha=2)

    primeira, segunda = (chamada["usuario"] for chamada in llm.chamadas_de(PapelModelo.GERADOR))
    assert '<trecho numero="0">' in primeira
    assert "Trecho 4 do material." in primeira
    assert "Não repita" not in primeira
    assert "Pergunta 1?" in segunda


async def test_questao_reprovada_e_refeita_com_as_criticas_do_revisor():
    llm = LLMFalso(avaliacoes=[avaliacao(nota=4, problemas=["Distratores óbvios"]), avaliacao()])
    prova = await gerar(llm, multipla_escolha=1)

    questao = prova.questoes[0]
    assert questao.aprovada
    assert questao.tentativas == 2
    segunda_geracao = llm.chamadas_de(PapelModelo.GERADOR)[1]["usuario"]
    assert "foi reprovada pelo revisor" in segunda_geracao
    assert "Distratores óbvios" in segunda_geracao


async def test_questao_sem_base_no_material_e_reprovada_mesmo_com_nota_alta():
    llm = LLMFalso(avaliacoes=[avaliacao(nota=10, fundamentada=False), avaliacao(nota=8)])
    prova = await gerar(llm, dissertativas=1)

    assert prova.questoes[0].tentativas == 2
    assert prova.questoes[0].avaliacao.nota == 8


async def test_sem_aprovacao_fica_a_melhor_tentativa():
    llm = LLMFalso(
        avaliacoes=[avaliacao(nota=6, problemas=["a"]), avaliacao(nota=3, problemas=["b"])]
    )
    prova = await gerar(llm, multipla_escolha=1)

    questao = prova.questoes[0]
    assert not questao.aprovada
    assert questao.avaliacao.nota == 6
    assert questao.conteudo.enunciado == "Pergunta 1?"
    assert questao.tentativas == 2


async def test_fontes_sao_os_trechos_citados_ou_todos_se_nenhum_valer():
    llm = LLMFalso(topicos=1)
    prova = await gerar(llm, multipla_escolha=1, dissertativas=1)

    multipla, dissertativa = prova.questoes
    assert [fonte.ordem for fonte in multipla.fontes] == [1, 3]  # o 99 não existe
    assert dissertativa.fontes == FONTES  # não citou nenhum


async def test_informa_o_progresso():
    eventos = []
    await gerar(LLMFalso(), ao_progredir=eventos.append, multipla_escolha=2, verdadeiro_falso=1)

    assert eventos[0].etapa == "planejamento"
    concluidas = [evento.concluidas for evento in eventos if evento.etapa == "geracao"]
    assert concluidas == [0, 1, 2, 3]
    assert all(evento.total == 3 for evento in eventos)


async def test_falha_de_um_agente_interrompe_a_prova():
    with pytest.raises(ErroSaidaLLM):
        await gerar(LLMFalso(falhar_em=QuestaoDissertativa), multipla_escolha=2, dissertativas=1)


async def test_revisor_recebe_so_os_criterios_do_tipo_da_questao():
    llm = LLMFalso(topicos=1)
    await gerar(llm, multipla_escolha=1, verdadeiro_falso=1)

    multipla, vf = (chamada["usuario"] for chamada in llm.chamadas_de(PapelModelo.REVISOR))
    assert "Exatamente uma alternativa correta" in multipla
    assert "Cada afirmativa" not in multipla
    assert "Cada afirmativa" in vf
    assert "Exatamente uma alternativa correta" not in vf
