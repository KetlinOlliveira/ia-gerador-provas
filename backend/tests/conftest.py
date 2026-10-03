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
from app.db.base import obter_fabrica_sessao
from app.db.modelos import DIMENSOES_EMBEDDING
from app.llm.cliente import obter_cliente_llm
from app.main import app
from app.rag.embeddings import obter_embedder
from tests.falsos import LLMFalso


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
    # DELETE em vez de TRUNCATE: com poucas linhas é bem mais rápido, porque o TRUNCATE
    # recria os arquivos das tabelas e paga o fsync lento do volume Docker no Windows.
    with engine.begin() as conexao:
        for tabela in ("provas", "trechos", "documentos"):
            conexao.execute(text(f"DELETE FROM {tabela}"))
    engine.dispose()


@pytest.fixture
def configuracoes():
    # Trechos pequenos para que textos curtos de teste gerem vários trechos.
    return Configuracoes(
        _env_file=None, tamanho_trecho=200, sobreposicao_trecho=40, tamanho_max_upload_mb=1
    )


@pytest.fixture
def fabrica_testes(engine_testes):
    return sessionmaker(engine_testes, expire_on_commit=False)


@pytest.fixture
def llm_falso():
    """Troque nos testes que precisam de outro comportamento: `llm_falso.falhar_em = ...`."""
    return LLMFalso()


@pytest.fixture
def cliente(fabrica_testes, configuracoes, llm_falso):
    embedder = EmbedderFalso()

    app.dependency_overrides[obter_configuracoes] = lambda: configuracoes
    app.dependency_overrides[obter_fabrica_sessao] = lambda: fabrica_testes
    app.dependency_overrides[obter_embedder] = lambda: embedder
    app.dependency_overrides[obter_cliente_llm] = lambda: llm_falso
    try:
        # Sem `with`: o ciclo de vida da aplicação (que usa o banco real) não roda.
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
