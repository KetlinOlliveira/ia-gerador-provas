from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import obter_configuracoes


class Base(DeclarativeBase):
    pass


@lru_cache
def obter_engine() -> Engine:
    return create_engine(obter_configuracoes().url_banco, pool_pre_ping=True)


@lru_cache
def obter_fabrica_sessao() -> sessionmaker[Session]:
    """Fábrica de sessões. Tarefas em segundo plano abrem as próprias sessões com ela,
    porque a sessão da requisição é fechada assim que a resposta sai."""
    return sessionmaker(obter_engine(), expire_on_commit=False)


def obter_sessao(
    fabrica: Annotated[sessionmaker[Session], Depends(obter_fabrica_sessao)],
) -> Iterator[Session]:
    with fabrica() as sessao:
        yield sessao
