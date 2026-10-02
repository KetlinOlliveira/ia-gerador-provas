import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import chromadb
from chromadb.config import Settings

from app.core.config import obter_configuracoes
from app.ingestao.divisor import Trecho


@dataclass(frozen=True)
class ResultadoBusca:
    trecho: Trecho
    pontuacao: float


class BancoVetorial(Protocol):
    def adicionar(
        self, documento_id: str, trechos: list[Trecho], vetores: list[list[float]]
    ) -> None: ...

    def buscar(self, documento_id: str, vetor: list[float], k: int) -> list[ResultadoBusca]: ...

    def remover(self, documento_id: str) -> None: ...


class BancoVetorialChroma:
    def __init__(self, diretorio: Path, nome_modelo: str) -> None:
        cliente = chromadb.PersistentClient(
            path=str(diretorio), settings=Settings(anonymized_telemetry=False)
        )
        # Uma coleção por modelo de embeddings: vetores de modelos diferentes não são
        # comparáveis, então trocar o modelo começa uma coleção nova em vez de corromper a atual.
        self._colecao = cliente.get_or_create_collection(
            name=_nome_da_colecao(nome_modelo),
            configuration={"hnsw": {"space": "cosine"}},
            embedding_function=None,
        )

    def adicionar(
        self, documento_id: str, trechos: list[Trecho], vetores: list[list[float]]
    ) -> None:
        self._colecao.add(
            ids=[f"{documento_id}:{trecho.ordem}" for trecho in trechos],
            embeddings=vetores,
            documents=[trecho.texto for trecho in trechos],
            metadatas=[_metadados(documento_id, trecho) for trecho in trechos],
        )

    def buscar(self, documento_id: str, vetor: list[float], k: int) -> list[ResultadoBusca]:
        resposta = self._colecao.query(
            query_embeddings=[vetor],
            n_results=k,
            where={"documento_id": documento_id},
            include=["documents", "metadatas", "distances"],
        )
        return [
            ResultadoBusca(
                trecho=Trecho(
                    ordem=metadados["ordem"], texto=texto, pagina=metadados.get("pagina")
                ),
                # O Chroma devolve distância de cosseno (0 = idêntico); a API expõe similaridade.
                pontuacao=1 - distancia,
            )
            for texto, metadados, distancia in zip(
                resposta["documents"][0],
                resposta["metadatas"][0],
                resposta["distances"][0],
                strict=True,
            )
        ]

    def remover(self, documento_id: str) -> None:
        self._colecao.delete(where={"documento_id": documento_id})


def _metadados(documento_id: str, trecho: Trecho) -> dict:
    metadados = {"documento_id": documento_id, "ordem": trecho.ordem}
    if trecho.pagina is not None:  # o Chroma não aceita None como valor de metadado
        metadados["pagina"] = trecho.pagina
    return metadados


def _nome_da_colecao(nome_modelo: str) -> str:
    sufixo = re.sub(r"[^a-zA-Z0-9]+", "-", nome_modelo).strip("-")[-50:].strip("-")
    return f"trechos-{sufixo}"


@lru_cache
def obter_banco_vetorial() -> BancoVetorial:
    configuracoes = obter_configuracoes()
    return BancoVetorialChroma(
        configuracoes.diretorio_dados / "chroma", configuracoes.modelo_embeddings
    )
