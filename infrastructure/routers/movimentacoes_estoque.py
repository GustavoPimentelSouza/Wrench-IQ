from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_movimentacao_estoque_repository import (
    SqlAlchemyMovimentacaoEstoqueRepository,
)
from adapters.sqlalchemy_peca_repository import SqlAlchemyPecaRepository
from application.movimentacao_estoque_use_cases import (
    EstoqueInsuficienteError,
    MovimentacaoEstoqueUseCases,
    PecaNaoEncontradaError,
)
from domain.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacao
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/movimentacoes-estoque", tags=["movimentacoes-estoque"])


class MovimentacaoEstoqueCreate(BaseModel):
    peca_id: UUID
    tipo: TipoMovimentacao
    quantidade: int


class MovimentacaoEstoqueOut(BaseModel):
    id: UUID
    peca_id: UUID
    tipo: TipoMovimentacao
    quantidade: int
    criado_em: datetime


def get_use_cases(session: AsyncSession = Depends(get_db)) -> MovimentacaoEstoqueUseCases:
    return MovimentacaoEstoqueUseCases(
        SqlAlchemyMovimentacaoEstoqueRepository(session), SqlAlchemyPecaRepository(session)
    )


@router.post("", response_model=MovimentacaoEstoqueOut, status_code=201)
async def registrar_movimentacao(
    payload: MovimentacaoEstoqueCreate,
    use_cases: MovimentacaoEstoqueUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> MovimentacaoEstoque:
    try:
        return await use_cases.registrar(
            payload.peca_id, payload.tipo, payload.quantidade
        )
    except PecaNaoEncontradaError:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    except EstoqueInsuficienteError:
        raise HTTPException(
            status_code=400, detail="Estoque insuficiente para essa saída"
        )


@router.get("", response_model=list[MovimentacaoEstoqueOut])
async def listar_movimentacoes(
    peca_id: UUID,
    use_cases: MovimentacaoEstoqueUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> list[MovimentacaoEstoque]:
    return await use_cases.listar_por_peca(peca_id)
