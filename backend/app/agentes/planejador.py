from app.agentes import prompts
from app.esquemas.provas import Fonte, PlanoProva
from app.llm.cliente import ClienteLLM, PapelModelo

# Acima disso a prova repete tópicos em vez de pulverizar o conteúdo.
MAX_TOPICOS = 8


async def planejar(llm: ClienteLLM, amostra: list[Fonte], total_questoes: int) -> PlanoProva:
    """Extrai do material os subtemas que a prova vai cobrir."""
    plano = await llm.completar_estruturado(
        papel=PapelModelo.PLANEJADOR,
        sistema=prompts.SISTEMA_PLANEJADOR,
        usuario=prompts.usuario_planejador(
            prompts.formatar_material(amostra), min(total_questoes, MAX_TOPICOS)
        ),
        esquema=PlanoProva,
        temperatura=0.2,
    )
    # O modelo às vezes devolve mais tópicos que o pedido ou repete algum.
    vistos: set[str] = set()
    topicos = []
    for topico in plano.topicos:
        chave = topico.titulo.strip().lower()
        if chave not in vistos:
            vistos.add(chave)
            topicos.append(topico)
    return PlanoProva(topicos=topicos[:MAX_TOPICOS])


def amostrar_material(trechos: list[Fonte], max_caracteres: int) -> list[Fonte]:
    """Escolhe trechos espalhados pelo documento inteiro, até `max_caracteres`.

    Um documento longo não cabe num prompt só. Pegar só o começo faria o plano
    ignorar os capítulos finais; trechos equidistantes cobrem o documento todo.
    """
    total = sum(len(trecho.texto) for trecho in trechos)
    if total <= max_caracteres:
        return trechos

    quantidade = max(1, len(trechos) * max_caracteres // total)
    passo = len(trechos) / quantidade
    return [trechos[int(indice * passo)] for indice in range(quantidade)]
