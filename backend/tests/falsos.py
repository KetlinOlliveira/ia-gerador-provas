"""Dublês compartilhados pelos testes: um LLM que responde conforme o esquema pedido."""

from app.core.excecoes import ErroSaidaLLM
from app.esquemas.provas import (
    Avaliacao,
    PlanoProva,
    QuestaoDissertativa,
    QuestaoMultiplaEscolha,
    QuestaoVerdadeiroFalso,
    Topico,
)


def avaliacao(nota=9, fundamentada=True, problemas=()):
    return Avaliacao(
        nota=nota,
        fundamentada=fundamentada,
        adequada_a_dificuldade=True,
        problemas=list(problemas),
        sugestoes="Corrija." if problemas else "",
    )


class LLMFalso:
    """Responde conforme o esquema pedido e registra cada chamada.

    `avaliacoes` são devolvidas em ordem pelo revisor; acabando, ele aprova tudo.
    """

    def __init__(self, topicos=3, avaliacoes=(), falhar_em=None):
        self.chamadas = []
        self._topicos = topicos
        self._avaliacoes = list(avaliacoes)
        self.falhar_em = falhar_em
        self._geradas = 0

    async def completar_estruturado(self, *, papel, sistema, usuario, esquema, **_):
        self.chamadas.append({"papel": papel, "usuario": usuario, "esquema": esquema})
        if esquema is self.falhar_em:
            raise ErroSaidaLLM("falhou")
        if esquema is PlanoProva:
            return PlanoProva(
                topicos=[
                    Topico(titulo=f"Tópico {i}", descricao="...") for i in range(self._topicos)
                ]
            )
        if esquema is Avaliacao:
            return self._avaliacoes.pop(0) if self._avaliacoes else avaliacao()

        self._geradas += 1
        n = self._geradas
        if esquema is QuestaoMultiplaEscolha:
            return QuestaoMultiplaEscolha(
                enunciado=f"Pergunta {n}?",
                alternativas=["a", "b", "c", "d"],
                resposta_correta="B",
                justificativa="...",
                trechos_usados=[1, 3, 99],
            )
        if esquema is QuestaoDissertativa:
            return QuestaoDissertativa(
                enunciado=f"Explique {n}.",
                resposta_esperada="...",
                criterios=[{"descricao": "x", "pontos": 5}, {"descricao": "y", "pontos": 5}],
                trechos_usados=[],
            )
        return QuestaoVerdadeiroFalso(
            enunciado="Julgue.",
            afirmativas=[
                {"texto": f"Afirmativa {n}a", "verdadeira": True, "justificativa": ""},
                {"texto": f"Afirmativa {n}b", "verdadeira": False, "justificativa": ""},
                {"texto": f"Afirmativa {n}c", "verdadeira": True, "justificativa": ""},
            ],
            trechos_usados=[0],
        )

    def chamadas_de(self, papel):
        return [chamada for chamada in self.chamadas if chamada["papel"] == papel]
