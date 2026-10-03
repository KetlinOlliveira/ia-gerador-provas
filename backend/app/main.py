import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.roteador import roteador_api
from app.core.config import obter_configuracoes
from app.core.excecoes import ErroAplicacao
from app.core.logs import configurar_logs
from app.db.base import obter_fabrica_sessao
from app.rag.embeddings import obter_embedder
from app.servicos.provas import marcar_provas_interrompidas

logger = logging.getLogger(__name__)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    interrompidas = await asyncio.to_thread(marcar_provas_interrompidas, obter_fabrica_sessao())
    if interrompidas:
        logger.warning(
            "%d prova(s) interrompida(s) por reinício marcadas como falha", interrompidas
        )
    # Carrega o modelo de embeddings em segundo plano, sem atrasar a subida, para que
    # o primeiro envio ou a primeira prova não paguem os segundos de carga.
    aquecimento = asyncio.create_task(asyncio.to_thread(_aquecer_embeddings))
    yield
    aquecimento.cancel()


def _aquecer_embeddings() -> None:
    try:
        obter_embedder().embutir_consulta("aquecimento")
    except Exception:
        logger.exception("Falha ao pré-carregar o modelo de embeddings")


def criar_app() -> FastAPI:
    configuracoes = obter_configuracoes()
    configurar_logs(configuracoes.nivel_log)

    # O esquema do banco é responsabilidade do Alembic (`alembic upgrade head`),
    # executado antes de a API subir; a aplicação não cria tabelas sozinha.
    app = FastAPI(title=configuracoes.nome_app, version=__version__, lifespan=ciclo_de_vida)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuracoes.origens_cors,
        allow_methods=["*"],
        allow_headers=["*"],
        # O navegador só deixa o frontend ler o nome do arquivo exportado se ele for exposto.
        expose_headers=["Content-Disposition"],
    )

    @app.exception_handler(ErroAplicacao)
    async def tratar_erro_aplicacao(_: Request, erro: ErroAplicacao) -> JSONResponse:
        return JSONResponse(
            status_code=erro.status_http,
            content={"erro": {"codigo": erro.codigo, "mensagem": erro.mensagem}},
        )

    app.include_router(roteador_api, prefix=configuracoes.prefixo_api)
    return app


app = criar_app()
