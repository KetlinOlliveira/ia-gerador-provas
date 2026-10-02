import pytest
from pydantic import ValidationError

from app.esquemas.provas import (
    ConfiguracaoProva,
    QuestaoDissertativa,
    QuestaoMultiplaEscolha,
    QuestaoVerdadeiroFalso,
)


def test_configuracao_exige_ao_menos_uma_questao():
    with pytest.raises(ValidationError, match="pelo menos uma questão"):
        ConfiguracaoProva(dificuldade="medio")

    configuracao = ConfiguracaoProva(dificuldade="medio", multipla_escolha=2, verdadeiro_falso=1)
    assert configuracao.total == 3


def test_multipla_escolha_exige_quatro_alternativas_distintas():
    base = {"enunciado": "?", "resposta_correta": "A", "justificativa": "", "trechos_usados": []}

    with pytest.raises(ValidationError):
        QuestaoMultiplaEscolha(alternativas=["a", "b", "c"], **base)
    with pytest.raises(ValidationError, match="diferentes"):
        QuestaoMultiplaEscolha(alternativas=["a", "b", "c", " A "], **base)


def test_criterios_da_dissertativa_somam_dez():
    base = {"enunciado": "?", "resposta_esperada": "", "trechos_usados": []}
    criterios = [{"descricao": "x", "pontos": 6}, {"descricao": "y", "pontos": 3}]

    with pytest.raises(ValidationError, match="somam 9"):
        QuestaoDissertativa(criterios=criterios, **base)

    criterios[1]["pontos"] = 4
    assert len(QuestaoDissertativa(criterios=criterios, **base).criterios) == 2


def test_verdadeiro_falso_mistura_verdadeiras_e_falsas():
    def afirmativas(*valores):
        return [
            {"texto": str(i), "verdadeira": v, "justificativa": ""} for i, v in enumerate(valores)
        ]

    with pytest.raises(ValidationError, match="verdadeira e uma falsa"):
        QuestaoVerdadeiroFalso(
            enunciado="Julgue.", afirmativas=afirmativas(True, True, True), trechos_usados=[]
        )

    questao = QuestaoVerdadeiroFalso(
        enunciado="Julgue.", afirmativas=afirmativas(True, False, True), trechos_usados=[]
    )
    assert questao.tipo == "verdadeiro_falso"


def test_multipla_escolha_remove_letras_escritas_pelo_modelo():
    questao = QuestaoMultiplaEscolha(
        enunciado="?",
        alternativas=["A) A) Primeira", "b. Segunda", "(C) Terceira", "D - Quarta"],
        resposta_correta="A",
        justificativa="",
        trechos_usados=[],
    )

    assert questao.alternativas == ["Primeira", "Segunda", "Terceira", "Quarta"]
