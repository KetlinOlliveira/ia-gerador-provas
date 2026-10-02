from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import __version__
from app.core.config import Configuracoes, obter_configuracoes

roteador = APIRouter(tags=["saúde"])


class RespostaSaude(BaseModel):
    status: str
    versao: str
    llm_configurado: bool


@roteador.get("/health")
def saude(configuracoes: Annotated[Configuracoes, Depends(obter_configuracoes)]) -> RespostaSaude:
    return RespostaSaude(
        status="ok",
        versao=__version__,
        llm_configurado=configuracoes.groq_api_key is not None,
    )
