import re
import zlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Configuracoes, obter_configuracoes
from app.db.base import criar_tabelas, obter_sessao
from app.main import app
from app.rag.banco_vetorial import BancoVetorialChroma, obter_banco_vetorial
from app.rag.embeddings import obter_embedder


class EmbedderFalso:
    """Vetoriza por contagem de palavras: textos com palavras em comum ficam próximos.

    Determinístico e instantâneo, para os testes não baixarem o modelo real.
    """

    nome_modelo = "falso"
    _dimensoes = 256

    def _vetor(self, texto: str) -> list[float]:
        vetor = [0.0] * self._dimensoes
        for palavra in re.findall(r"\w+", texto.lower()):
            vetor[zlib.crc32(palavra.encode()) % self._dimensoes] += 1.0
        return vetor

    def embutir_trechos(self, textos: list[str]) -> list[list[float]]:
        return [self._vetor(texto) for texto in textos]

    def embutir_consulta(self, consulta: str) -> list[float]:
        return self._vetor(consulta)


@pytest.fixture
def configuracoes():
    # Trechos pequenos para que textos curtos de teste gerem vários trechos.
    return Configuracoes(
        _env_file=None, tamanho_trecho=200, sobreposicao_trecho=40, tamanho_max_upload_mb=1
    )


@pytest.fixture
def cliente(tmp_path, configuracoes):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'teste.db'}", connect_args={"check_same_thread": False}
    )
    criar_tabelas(engine)
    fabrica = sessionmaker(engine, expire_on_commit=False)
    banco_vetorial = BancoVetorialChroma(tmp_path / "chroma", "falso")
    embedder = EmbedderFalso()

    def sessao_de_teste():
        with fabrica() as sessao:
            yield sessao

    app.dependency_overrides[obter_configuracoes] = lambda: configuracoes
    app.dependency_overrides[obter_sessao] = sessao_de_teste
    app.dependency_overrides[obter_banco_vetorial] = lambda: banco_vetorial
    app.dependency_overrides[obter_embedder] = lambda: embedder
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
