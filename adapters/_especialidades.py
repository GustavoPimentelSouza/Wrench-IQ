from sqlalchemy import Table, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.especialidade import Especialidade

# Helper compartilhado pelos 3 repositories que têm especialidade N:N
# (Protocolo, Agendamento, Usuario/mecânico) — é a mesma operação (carregar
# lista, substituir lista inteira) em 3 tabelas de junção diferentes,
# então vale reaproveitar em vez de repetir 3x a mesma query.


async def carregar(session: AsyncSession, tabela: Table, coluna_id: str, entidade_id) -> list[Especialidade]:
    result = await session.execute(
        select(tabela.c.especialidade).where(tabela.c[coluna_id] == entidade_id)
    )
    return [Especialidade(valor) for (valor,) in result.all()]


async def substituir(
    session: AsyncSession,
    tabela: Table,
    coluna_id: str,
    entidade_id,
    especialidades: list[Especialidade],
) -> None:
    # Sempre apaga e reinsere tudo — mais simples que calcular diff
    # (adicionar só as novas, remover só as que saíram), e o volume por
    # protocolo/agendamento/mecânico é sempre pequeno (no máximo 4 linhas).
    await session.execute(delete(tabela).where(tabela.c[coluna_id] == entidade_id))
    if especialidades:
        await session.execute(
            insert(tabela),
            [{coluna_id: entidade_id, "especialidade": e.value} for e in especialidades],
        )
