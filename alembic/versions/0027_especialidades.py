"""criar especialidade e tabelas de junção (protocolo/agendamento/mecanico)

Revision ID: 0027
Revises: 0026
Create Date: 2026-08-06

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "protocolo_especialidades",
        sa.Column(
            "protocolo_id",
            UUID(as_uuid=True),
            sa.ForeignKey("protocolos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("especialidade", sa.String(), primary_key=True),
    )
    op.create_table(
        "agendamento_especialidades",
        sa.Column(
            "agendamento_id",
            UUID(as_uuid=True),
            sa.ForeignKey("agendamentos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("especialidade", sa.String(), primary_key=True),
    )
    op.create_table(
        "mecanico_especialidades",
        sa.Column(
            "usuario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("especialidade", sa.String(), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("mecanico_especialidades")
    op.drop_table("agendamento_especialidades")
    op.drop_table("protocolo_especialidades")
