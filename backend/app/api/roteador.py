from fastapi import APIRouter

from app.api.rotas import documentos, provas, saude

roteador_api = APIRouter()
roteador_api.include_router(saude.roteador)
roteador_api.include_router(documentos.roteador)
roteador_api.include_router(provas.roteador)
