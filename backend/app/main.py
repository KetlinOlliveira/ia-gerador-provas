from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.roteador import roteador_api
from app.core.config import obter_configuracoes
from app.core.excecoes import ErroAplicacao
from app.core.logs import configurar_logs


def criar_app() -> FastAPI:
    configuracoes = obter_configuracoes()
    configurar_logs(configuracoes.nivel_log)

    # O esquema do banco é responsabilidade do Alembic (`alembic upgrade head`),
    # executado antes de a API subir; a aplicação não cria tabelas sozinha.
    app = FastAPI(title=configuracoes.nome_app, version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuracoes.origens_cors,
        allow_methods=["*"],
        allow_headers=["*"],
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
