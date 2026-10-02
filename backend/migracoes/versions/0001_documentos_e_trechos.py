"""Cria documentos e trechos com embeddings (pgvector)

Revisão: 0001
Anterior:
Criada em: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documentos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nome_arquivo", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=False),
        sa.Column("hash_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("total_caracteres", sa.Integer(), nullable=False),
        sa.Column("total_trechos", sa.Integer(), nullable=False),
        sa.Column("total_paginas", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "trechos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "documento_id",
            sa.String(36),
            sa.ForeignKey("documentos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("pagina", sa.Integer(), nullable=True),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
    )
    op.create_index("ix_trechos_documento_id", "trechos", ["documento_id"])


def downgrade() -> None:
    op.drop_index("ix_trechos_documento_id", table_name="trechos")
    op.drop_table("trechos")
    op.drop_table("documentos")
