from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_protocolo_repository import SqlAlchemyProtocoloRepository
from adapters.sqlalchemy_reclassificacao_repository import SqlAlchemyReclassificacaoRepository
from application.relatorio_use_cases import RelatorioTaxaReclassificacao, RelatorioUseCases
from domain.especialidade import Especialidade
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import exigir_admin

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


class TaxaPorEspecialidadeOut(BaseModel):
    especialidade: Especialidade
    total_reclassificacoes: int


class RelatorioTaxaReclassificacaoOut(BaseModel):
    periodo_inicio: date
    periodo_fim: date
    total_protocolos: int
    total_reclassificados: int
    taxa: float
    por_especialidade: list[TaxaPorEspecialidadeOut]


def get_use_cases(session: AsyncSession = Depends(get_db)) -> RelatorioUseCases:
    return RelatorioUseCases(
        SqlAlchemyReclassificacaoRepository(session), SqlAlchemyProtocoloRepository(session)
    )


# Só admin: expõe quão certeira a classificação automática está sendo — dado
# sensível de qualidade do produto, não é operacional do dia a dia de
# atendente/mecânico (ver infrastructure/security_dependencies.exigir_admin).
@router.get("/taxa-reclassificacao", response_model=RelatorioTaxaReclassificacaoOut)
async def taxa_reclassificacao(
    inicio: date,
    fim: date,
    use_cases: RelatorioUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(exigir_admin),
) -> RelatorioTaxaReclassificacao:
    return await use_cases.taxa_reclassificacao(inicio, fim)
