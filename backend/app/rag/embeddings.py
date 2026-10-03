import threading
from functools import lru_cache
from typing import Protocol

from fastembed import TextEmbedding

from app.core.config import obter_configuracoes
from app.db.modelos import DIMENSOES_EMBEDDING


class Embedder(Protocol):
    """Transforma texto em vetores. Trechos e consultas têm métodos separados
    porque alguns modelos usam prefixos diferentes para cada um."""

    nome_modelo: str

    def embutir_trechos(self, textos: list[str]) -> list[list[float]]: ...

    def embutir_consulta(self, consulta: str) -> list[float]: ...


class EmbedderLocal:
    """Embeddings locais via fastembed (ONNX, em CPU), sem chamada a API externa."""

    def __init__(self, nome_modelo: str, diretorio_cache: str, somente_local: bool) -> None:
        dimensoes = TextEmbedding.get_embedding_size(nome_modelo)
        if dimensoes != DIMENSOES_EMBEDDING:
            raise ValueError(
                f"O modelo {nome_modelo} gera vetores de {dimensoes} dimensões, mas a "
                f"coluna do banco espera {DIMENSOES_EMBEDDING}. Crie uma migração antes de trocar."
            )
        self.nome_modelo = nome_modelo
        self._diretorio_cache = diretorio_cache
        self._somente_local = somente_local
        self._modelo: TextEmbedding | None = None
        # O aquecimento na subida e a primeira requisição podem chegar juntos.
        self._trava = threading.Lock()

    def _obter_modelo(self) -> TextEmbedding:
        # Carregado no primeiro uso. Fora do Docker, na primeira vez, o modelo
        # também é baixado nesse momento.
        with self._trava:
            if self._modelo is None:
                self._modelo = TextEmbedding(
                    self.nome_modelo,
                    cache_dir=self._diretorio_cache,
                    local_files_only=self._somente_local,
                )
            return self._modelo

    def embutir_trechos(self, textos: list[str]) -> list[list[float]]:
        return [vetor.tolist() for vetor in self._obter_modelo().passage_embed(textos)]

    def embutir_consulta(self, consulta: str) -> list[float]:
        return next(iter(self._obter_modelo().query_embed(consulta))).tolist()


@lru_cache
def obter_embedder() -> Embedder:
    configuracoes = obter_configuracoes()
    return EmbedderLocal(
        configuracoes.modelo_embeddings,
        diretorio_cache=str(configuracoes.diretorio_modelos),
        somente_local=configuracoes.embeddings_somente_local,
    )
