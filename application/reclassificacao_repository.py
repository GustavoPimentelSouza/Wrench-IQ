from datetime import date
from typing import Protocol

from domain.reclassificacao_especialidade import ReclassificacaoEspecialidade


class ReclassificacaoRepository(Protocol):
    async def criar(
        self, reclassificacao: ReclassificacaoEspecialidade
    ) -> ReclassificacaoEspecialidade: ...

    # Usado por RelatorioUseCases.taxa_reclassificacao — período inclusivo
    # dos dois lados.
    async def listar_por_periodo(
        self, inicio: date, fim: date
    ) -> list[ReclassificacaoEspecialidade]: ...
