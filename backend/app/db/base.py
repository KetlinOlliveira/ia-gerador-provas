from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import obter_configuracoes


class Base(DeclarativeBase):
    pass


@lru_cache
def obter_engine() -> Engine:
    return create_engine(obter_configuracoes().url_banco, pool_pre_ping=True)


def obter_sessao() -> Iterator[Session]:
    with sessionmaker(obter_engine(), expire_on_commit=False)() as sessao:
        yield sessao
