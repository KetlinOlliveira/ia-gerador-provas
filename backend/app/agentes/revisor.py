from app.agentes import prompts
from app.agentes.gerador import Questao
from app.esquemas.provas import Avaliacao, Dificuldade, Fonte, TipoQuestao
from app.llm.cliente import ClienteLLM, PapelModelo


async def revisar(
    llm: ClienteLLM,
    questao: Questao,
    topico: str,
    dificuldade: Dificuldade,
    fontes: list[Fonte],
) -> Avaliacao:
    """Avalia a questão contra os mesmos trechos que o gerador usou."""
    return await llm.completar_estruturado(
        papel=PapelModelo.REVISOR,
        sistema=prompts.SISTEMA_REVISOR,
        usuario=prompts.usuario_revisor(
            questao.model_dump_json(exclude={"trechos_usados"}),
            TipoQuestao(questao.tipo),
            topico,
            dificuldade,
            prompts.formatar_material(fontes),
        ),
        esquema=Avaliacao,
        temperatura=0.1,
    )


def aprovada(avaliacao: Avaliacao, nota_minima: int) -> bool:
    # A decisão é do código, não do modelo: nota suficiente e gabarito sustentado
    # pelo material. Uma questão bem escrita, mas sem base nos trechos, não passa.
    return avaliacao.fundamentada and avaliacao.nota >= nota_minima
