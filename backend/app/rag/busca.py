from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.modelos import Trecho


@dataclass(frozen=True)
class ResultadoBusca:
    trecho: Trecho
    pontuacao: float


def buscar_trechos_semelhantes(
    sessao: Session, documento_id: str, vetor: list[float], k: int
) -> list[ResultadoBusca]:
    """Os `k` trechos do documento mais próximos do vetor, por distância de cosseno.

    A busca é exata, sem índice aproximado (HNSW): filtrada por documento, ela
    percorre só algumas centenas de linhas, o que é rápido e nunca perde resultados.
    Um índice HNSW passa a valer quando houver busca entre todos os documentos.
    """
    distancia = Trecho.embedding.cosine_distance(vetor)
    linhas = sessao.execute(
        select(Trecho, distancia)
        .where(Trecho.documento_id == documento_id)
        .order_by(distancia)
        .limit(k)
    )
    # A API expõe similaridade (1 = idêntico), mais intuitiva que distância.
    return [ResultadoBusca(trecho=trecho, pontuacao=1 - dist) for trecho, dist in linhas]
