from fastapi import APIRouter

from app.api.rotas import saude

roteador_api = APIRouter()
roteador_api.include_router(saude.roteador)
