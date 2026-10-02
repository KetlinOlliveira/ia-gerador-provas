from datetime import UTC, datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Tamanho dos vetores do modelo de embeddings configurado. Trocar para um modelo
# com outra dimensão exige uma migração que altere a coluna e reindexe os trechos.
DIMENSOES_EMBEDDING = 384


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
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    trechos: Mapped[list["Trecho"]] = relationship(
        back_populates="documento",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Trecho.ordem",
    )


class Trecho(Base):
    __tablename__ = "trechos"

    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[str] = mapped_column(
        ForeignKey("documentos.id", ondelete="CASCADE"), index=True
    )
    ordem: Mapped[int]
    pagina: Mapped[int | None]
    texto: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(DIMENSOES_EMBEDDING))

    documento: Mapped[Documento] = relationship(back_populates="trechos")
