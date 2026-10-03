from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Configuracoes, obter_configuracoes

roteador = APIRouter(tags=["sistema"])


class ModelosAgentes(BaseModel):
    planejador: str
    gerador: str
    revisor: str


class InformacoesSistema(BaseModel):
    """Configuração do pipeline exposta à interface. Nada aqui é segredo."""

    modelos: ModelosAgentes
    modelo_embeddings: str
    tamanho_trecho: int
    trechos_por_topico: int
    nota_minima_revisao: int
    max_tentativas_por_questao: int
    tamanho_max_upload_mb: int


@roteador.get("/sistema")
def informacoes(
    configuracoes: Annotated[Configuracoes, Depends(obter_configuracoes)],
) -> InformacoesSistema:
    return InformacoesSistema(
        modelos=ModelosAgentes(
            planejador=configuracoes.modelo_planejador,
            gerador=configuracoes.modelo_gerador,
            revisor=configuracoes.modelo_revisor,
        ),
        modelo_embeddings=configuracoes.modelo_embeddings,
        tamanho_trecho=configuracoes.tamanho_trecho,
        trechos_por_topico=configuracoes.trechos_por_topico,
        nota_minima_revisao=configuracoes.nota_minima_revisao,
        max_tentativas_por_questao=configuracoes.max_tentativas_por_questao,
        tamanho_max_upload_mb=configuracoes.tamanho_max_upload_mb,
    )
