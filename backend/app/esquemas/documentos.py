from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome_arquivo: str
    tipo: str
    tamanho_bytes: int
    total_caracteres: int
    total_trechos: int
    total_paginas: int | None
    criado_em: datetime


class BuscaRequisicao(BaseModel):
    consulta: str = Field(min_length=1, max_length=500)
    k: int = Field(default=5, ge=1, le=20)


class TrechoEncontrado(BaseModel):
    ordem: int
    pagina: int | None
    texto: str
    pontuacao: float = Field(description="Similaridade de cosseno entre a consulta e o trecho.")
