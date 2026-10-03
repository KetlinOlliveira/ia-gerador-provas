import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Configuracoes, obter_configuracoes
from app.core.excecoes import ErroConflito, ErroNaoEncontrado
from app.db.base import obter_fabrica_sessao
from app.esquemas.provas import (
    STATUS_FINAIS,
    CriarProvaRequisicao,
    Dificuldade,
    EstatisticasProvas,
    PaginaProvas,
    ProvaDetalhe,
    ProvaResumo,
    StatusProva,
)
from app.exportacao.conteudo import Versao
from app.exportacao.formatos import Formato, exportar
from app.llm.cliente import ClienteLLM, obter_cliente_llm
from app.rag.embeddings import Embedder, obter_embedder
from app.servicos.geracao import GeradorDeProvas
from app.servicos.provas import ServicoProvas

roteador = APIRouter(prefix="/provas", tags=["provas"])

# Intervalo com que o fluxo de eventos consulta o banco. A geração leva dezenas de
# segundos; meio segundo é imperceptível para quem acompanha e barato para o banco.
INTERVALO_EVENTOS_SEGUNDOS = 0.5


def obter_servico(
    fabrica: Annotated[sessionmaker[Session], Depends(obter_fabrica_sessao)],
    embedder: Annotated[Embedder, Depends(obter_embedder)],
    llm: Annotated[ClienteLLM, Depends(obter_cliente_llm)],
    configuracoes: Annotated[Configuracoes, Depends(obter_configuracoes)],
) -> ServicoProvas:
    return ServicoProvas(fabrica, GeradorDeProvas(fabrica, embedder, llm, configuracoes))


Servico = Annotated[ServicoProvas, Depends(obter_servico)]


@roteador.post("", status_code=status.HTTP_202_ACCEPTED)
def criar_prova(
    requisicao: CriarProvaRequisicao, servico: Servico, tarefas: BackgroundTasks
) -> ProvaResumo:
    """Registra a prova e devolve na hora; a geração continua em segundo plano.

    Acompanhe por `GET /provas/{id}/eventos` (SSE) ou consultando `GET /provas/{id}`.
    """
    prova = servico.criar(requisicao)
    tarefas.add_task(servico.executar, prova.id)
    return prova


@roteador.get("")
def listar_provas(
    servico: Servico,
    busca: Annotated[str | None, Query(max_length=100)] = None,
    dificuldade: Dificuldade | None = None,
    ordem: Literal["recentes", "antigas"] = "recentes",
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=50)] = 5,
) -> PaginaProvas:
    return servico.listar(
        busca=busca,
        dificuldade=dificuldade,
        mais_antigas_primeiro=ordem == "antigas",
        pagina=pagina,
        por_pagina=por_pagina,
    )


@roteador.get("/estatisticas")
def estatisticas(servico: Servico) -> EstatisticasProvas:
    return servico.estatisticas()


@roteador.get("/{prova_id}")
def obter_prova(prova_id: str, servico: Servico) -> ProvaDetalhe:
    return servico.obter(prova_id)


@roteador.delete("/{prova_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_prova(prova_id: str, servico: Servico) -> None:
    servico.excluir(prova_id)


@roteador.get("/{prova_id}/eventos")
async def acompanhar_prova(prova_id: str, request: Request, servico: Servico) -> StreamingResponse:
    """Server-Sent Events: um evento `progresso` a cada mudança e um `fim` ao terminar."""
    # Valida antes de abrir o fluxo, para que uma prova inexistente vire 404 normal.
    await asyncio.to_thread(servico.obter_progresso, prova_id)

    async def eventos() -> AsyncIterator[str]:
        anterior = None
        while not await request.is_disconnected():
            try:
                progresso = await asyncio.to_thread(servico.obter_progresso, prova_id)
            except ErroNaoEncontrado:
                yield _evento("fim", {"status": "excluida"})
                return
            dados = progresso.model_dump(mode="json")
            if dados != anterior:
                yield _evento("progresso", dados)
                anterior = dados
            if progresso.status in STATUS_FINAIS:
                yield _evento("fim", dados)
                return
            await asyncio.sleep(INTERVALO_EVENTOS_SEGUNDOS)

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        # Sem isso, proxies como o nginx acumulam os eventos e entregam tudo no final.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@roteador.get("/{prova_id}/exportar")
def exportar_prova(
    prova_id: str,
    servico: Servico,
    formato: Formato = Formato.PDF,
    versao: Versao = Versao.ALUNO,
) -> Response:
    prova = servico.obter(prova_id)
    if prova.status != StatusProva.CONCLUIDA:
        raise ErroConflito("A prova ainda não foi concluída, então não pode ser exportada.")
    arquivo = exportar(prova, formato, versao)
    return Response(
        content=arquivo.conteudo,
        media_type=arquivo.tipo_midia,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(arquivo.nome)}"},
    )


def _evento(nome: str, dados: dict) -> str:
    return f"event: {nome}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"
