from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


class DataHoraUTC(TypeDecorator):
    """O SQLite não guarda fuso horário: sem isto, a data sai com fuso na criação
    e sem fuso nas leituras seguintes. Aqui ela é sempre gravada e lida em UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, valor: datetime | None, dialect) -> datetime | None:
        return valor.astimezone(UTC).replace(tzinfo=None) if valor else valor

    def process_result_value(self, valor: datetime | None, dialect) -> datetime | None:
        return valor.replace(tzinfo=UTC) if valor else valor


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    nome_arquivo: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(10))
    tamanho_bytes: Mapped[int]
    # Identifica o conteúdo: reenviar o mesmo arquivo não gera embeddings de novo.
    hash_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    total_caracteres: Mapped[int]
    total_trechos: Mapped[int]
    total_paginas: Mapped[int | None]
    criado_em: Mapped[datetime] = mapped_column(DataHoraUTC, default=lambda: datetime.now(UTC))
