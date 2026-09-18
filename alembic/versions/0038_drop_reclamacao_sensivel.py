"""remapear registros antigos com categoria/motivo 'reclamacao_sensivel'

Revision ID: 0038
Revises: 0037
Create Date: 2026-09-03

Reclamação deixou de ter categoria e motivo próprios — a IA transfere pelo
mecanismo genérico (transferir_atendimento já está em todas as listas de
ferramentas, regra 4 do CLAUDE.md). Como os enums CategoriaMensagem e
MotivoAtendimento não têm mais 'reclamacao_sensivel', qualquer registro
antigo com esse valor quebraria ao ser carregado (CategoriaMensagem(...) /
MotivoAtendimento(...) levantam ValueError). Só há remapeamento de dado;
nenhuma mudança de schema. A migração 0022, que criou o backfill original
desse valor, permanece intacta — histórico de schema nunca é editado.
"""
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Categoria antiga de reclamação vira o catch-all 'nao_identificado' —
    # é o rótulo que sobrou pra "não classificamos isso em nada específico".
    op.execute(
        "UPDATE mensagens SET categoria = 'nao_identificado' "
        "WHERE categoria = 'reclamacao_sensivel'"
    )
    # O motivo 'reclamacao_sensivel' era sempre um caso de escalar pra
    # humano; o equivalente que sobrou é 'transferencia_ia' (a IA decidiu no
    # meio da conversa que precisa de gente).
    op.execute(
        "UPDATE mensagens SET motivo_atendimento = 'transferencia_ia' "
        "WHERE motivo_atendimento = 'reclamacao_sensivel'"
    )


def downgrade() -> None:
    # Só de dado e sem fidelidade pra reverter: não dá pra saber quais
    # registros 'nao_identificado' / 'transferencia_ia' vieram de reclamação.
    # Sem schema pra desfazer, o downgrade é no-op de propósito.
    pass
