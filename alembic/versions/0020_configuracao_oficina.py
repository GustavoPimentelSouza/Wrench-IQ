"""criar tabela configuracao_oficina (horario de funcionamento)

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-03

"""
import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracao_oficina",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("horario_semana_abertura", sa.Time(), nullable=False),
        sa.Column("horario_semana_fechamento", sa.Time(), nullable=False),
        sa.Column("horario_sabado_abertura", sa.Time(), nullable=True),
        sa.Column("horario_sabado_fechamento", sa.Time(), nullable=True),
        sa.Column("horario_domingo_abertura", sa.Time(), nullable=True),
        sa.Column("horario_domingo_fechamento", sa.Time(), nullable=True),
    )
    # Semeia a linha única já com o horário real combinado com a oficina —
    # sem isso, a IA ficaria sem dado nenhum até alguém abrir a tela de
    # configurações pela primeira vez.
    op.execute(
        """
        INSERT INTO configuracao_oficina (
            id, horario_semana_abertura, horario_semana_fechamento,
            horario_sabado_abertura, horario_sabado_fechamento,
            horario_domingo_abertura, horario_domingo_fechamento
        ) VALUES (1, '08:00', '19:00', '08:00', '18:00', '08:00', '12:00')
        """
    )


def downgrade() -> None:
    op.drop_table("configuracao_oficina")
