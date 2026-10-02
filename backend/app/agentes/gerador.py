from pydantic import BaseModel

from app.agentes import prompts
from app.esquemas.provas import (
    Avaliacao,
    Dificuldade,
    Fonte,
    QuestaoDissertativa,
    QuestaoMultiplaEscolha,
    QuestaoVerdadeiroFalso,
    TipoQuestao,
)
from app.llm.cliente import ClienteLLM, PapelModelo

ESQUEMAS: dict[TipoQuestao, type[BaseModel]] = {
    TipoQuestao.MULTIPLA_ESCOLHA: QuestaoMultiplaEscolha,
    TipoQuestao.DISSERTATIVA: QuestaoDissertativa,
    TipoQuestao.VERDADEIRO_FALSO: QuestaoVerdadeiroFalso,
}

Questao = QuestaoMultiplaEscolha | QuestaoDissertativa | QuestaoVerdadeiroFalso


async def gerar_questao(
    llm: ClienteLLM,
    *,
    tipo: TipoQuestao,
    topico: str,
    dificuldade: Dificuldade,
    fontes: list[Fonte],
    letra_correta: str | None = None,
    evitar: list[str] | None = None,
    anterior: tuple[Questao, Avaliacao] | None = None,
) -> Questao:
    """Gera uma questão a partir dos trechos recuperados.

    `anterior` é a versão reprovada e a avaliação do revisor: o gerador recebe os
    problemas apontados e tenta corrigi-los, em vez de só tentar de novo às cegas.
    """
    revisao_anterior = None
    if anterior is not None:
        questao, avaliacao = anterior
        revisao_anterior = prompts.descrever_revisao(
            questao.model_dump_json(), avaliacao.problemas, avaliacao.sugestoes
        )

    return await llm.completar_estruturado(
        papel=PapelModelo.GERADOR,
        sistema=prompts.SISTEMA_GERADOR,
        usuario=prompts.usuario_gerador(
            tipo,
            topico,
            dificuldade,
            prompts.formatar_material(fontes),
            letra_correta,
            evitar or [],
            revisao_anterior,
        ),
        esquema=ESQUEMAS[tipo],
        temperatura=0.7,
    )
