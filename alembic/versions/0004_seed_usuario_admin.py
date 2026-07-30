"""seed usuario admin padrao

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-23

"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_ADMIN_EMAIL = "admin@wrenchiq.com"
# bcrypt hash da senha de desenvolvimento "admin123" (ver README, seção Auth JWT)
_ADMIN_SENHA_HASH = "$2b$12$1ar0lLovAnR4D/V8JLBjz.8NVazcI9YcjuKZ4rxLFNGosW1xlJcmO"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO usuarios (id, nome, email, senha_hash, papel, ativo, criado_em)
            VALUES (
                '00000000-0000-0000-0000-000000000001',
                'Administrador',
                :email,
                :senha_hash,
                'admin',
                true,
                now()
            )
            """
        ).bindparams(email=_ADMIN_EMAIL, senha_hash=_ADMIN_SENHA_HASH)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM usuarios WHERE email = :email").bindparams(
            email=_ADMIN_EMAIL
        )
    )
