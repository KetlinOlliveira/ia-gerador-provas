from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import obter_configuracoes


class Base(DeclarativeBase):
    pass


@lru_cache
def obter_engine() -> Engine:
    configuracoes = obter_configuracoes()
    configuracoes.diretorio_dados.mkdir(parents=True, exist_ok=True)
    caminho = configuracoes.diretorio_dados / "app.db"
    # As rotas síncronas rodam no pool de threads do FastAPI, então a conexão
    # do SQLite precisa poder ser usada fora da thread que a criou.
    return create_engine(f"sqlite:///{caminho}", connect_args={"check_same_thread": False})


def criar_tabelas(engine: Engine) -> None:
    from app.db import modelos  # noqa: F401  (registra os modelos na Base)

    Base.metadata.create_all(engine)


def obter_sessao() -> Iterator[Session]:
    with sessionmaker(obter_engine(), expire_on_commit=False)() as sessao:
        yield sessao
