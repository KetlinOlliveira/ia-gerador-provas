from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import obter_configuracoes
from app.db import modelos  # noqa: F401  (registra os modelos na Base)
from app.db.base import Base

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def _url() -> str:
    # Os testes passam a URL do banco de testes por aqui; o normal é usar a da aplicação.
    return context.config.attributes.get("url_banco") or obter_configuracoes().url_banco


def executar_offline() -> None:
    context.configure(url=_url(), target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def executar_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as conexao:
        context.configure(connection=conexao, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    executar_offline()
else:
    executar_online()
