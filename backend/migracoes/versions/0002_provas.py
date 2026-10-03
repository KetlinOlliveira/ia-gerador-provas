"""Cria a tabela de provas (histórico e acompanhamento da geração)

Revisão: 0002
Anterior: 0001
Criada em: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "documento_id",
            sa.String(36),
            sa.ForeignKey("documentos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("dificuldade", sa.String(10), nullable=False),
        sa.Column("total_questoes", sa.Integer(), nullable=False),
        sa.Column("configuracao", JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("etapa", sa.String(20), nullable=True),
        sa.Column("mensagem", sa.String(255), nullable=True),
        sa.Column("questoes_concluidas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("resultado", JSONB(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duracao_segundos", sa.Float(), nullable=True),
    )
    op.create_index("ix_provas_documento_id", "provas", ["documento_id"])
    op.create_index("ix_provas_status", "provas", ["status"])
    op.create_index("ix_provas_criado_em", "provas", ["criado_em"])


def downgrade() -> None:
    op.drop_index("ix_provas_criado_em", table_name="provas")
    op.drop_index("ix_provas_status", table_name="provas")
    op.drop_index("ix_provas_documento_id", table_name="provas")
    op.drop_table("provas")
