import os
import re
import zlib

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import Configuracoes, obter_configuracoes
from app.db.base import obter_sessao
from app.db.modelos import DIMENSOES_EMBEDDING
from app.main import app
from app.rag.embeddings import obter_embedder


class EmbedderFalso:
    """Vetoriza por contagem de palavras: textos com palavras em comum ficam próximos.

    Determinístico e instantâneo, para os testes não carregarem o modelo real.
    """

    nome_modelo = "falso"

    def _vetor(self, texto: str) -> list[float]:
        vetor = [0.0] * DIMENSOES_EMBEDDING
        for palavra in re.findall(r"\w+", texto.lower()):
            vetor[zlib.crc32(palavra.encode()) % DIMENSOES_EMBEDDING] += 1.0
        return vetor

    def embutir_trechos(self, textos: list[str]) -> list[list[float]]:
        return [self._vetor(texto) for texto in textos]

    def embutir_consulta(self, consulta: str) -> list[float]:
        return self._vetor(consulta)


@pytest.fixture(scope="session")
def url_banco_testes():
    """Banco `provas_testes` no mesmo Postgres da aplicação, criado e migrado uma vez.

    Pode ser apontado para outro servidor com a variável URL_BANCO_TESTES.
    """
    url = make_url(
        os.environ.get("URL_BANCO_TESTES")
        or Configuracoes(_env_file=None).url_banco.rsplit("/", 1)[0] + "/provas_testes"
    )

    servidor = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with servidor.connect() as conexao:
            existe = conexao.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :nome"), {"nome": url.database}
            )
            if not existe:
                conexao.execute(text(f'CREATE DATABASE "{url.database}"'))
    except Exception as erro:
        pytest.exit(
            f"Postgres de testes indisponível em {url.render_as_string(hide_password=True)}. "
            f"Suba o banco com `docker compose up -d db`. Erro: {erro}",
            returncode=1,
        )
    finally:
        servidor.dispose()

    url_texto = url.render_as_string(hide_password=False)
    config_alembic = Config("alembic.ini")
    config_alembic.attributes["url_banco"] = url_texto
    command.upgrade(config_alembic, "head")
    return url_texto


@pytest.fixture
def engine_testes(url_banco_testes):
    engine = create_engine(url_banco_testes)
    yield engine
    with engine.begin() as conexao:
        conexao.execute(text("TRUNCATE documentos, trechos RESTART IDENTITY CASCADE"))
    engine.dispose()


@pytest.fixture
def configuracoes():
    # Trechos pequenos para que textos curtos de teste gerem vários trechos.
    return Configuracoes(
        _env_file=None, tamanho_trecho=200, sobreposicao_trecho=40, tamanho_max_upload_mb=1
    )


@pytest.fixture
def cliente(engine_testes, configuracoes):
    fabrica = sessionmaker(engine_testes, expire_on_commit=False)
    embedder = EmbedderFalso()

    def sessao_de_teste():
        with fabrica() as sessao:
            yield sessao

    app.dependency_overrides[obter_configuracoes] = lambda: configuracoes
    app.dependency_overrides[obter_sessao] = sessao_de_teste
    app.dependency_overrides[obter_embedder] = lambda: embedder
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
