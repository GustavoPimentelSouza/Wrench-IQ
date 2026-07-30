"""adicionar endereco e cpf_cnpj em clientes

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("endereco", sa.String(), nullable=True))
    op.add_column("clientes", sa.Column("cpf_cnpj", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("clientes", "cpf_cnpj")
    op.drop_column("clientes", "endereco")
