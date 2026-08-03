from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_peca_repository import SqlAlchemyPecaRepository
from application.embedding_service import EmbeddingService
from application.peca_repository import PecaPossuiPedidosError
from application.peca_use_cases import PecaUseCases
from domain.peca import Peca
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.ia import get_embedding_service
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/pecas", tags=["pecas"])


# Create/Update/Out separados de propósito: Create/Update é o que o cliente
# manda (nunca id/criado_em); Out é o que a API devolve.
class PecaCreate(BaseModel):
    nome: str
    marca_modelo_compativel: str
    ano_compativel: str
    preco: Decimal
    quantidade_estoque: int
    imagem_url: str | None = None
    quantidade_minima: int = 0


class PecaUpdate(BaseModel):
    nome: str
    marca_modelo_compativel: str
    ano_compativel: str
    preco: Decimal
    quantidade_estoque: int
    imagem_url: str | None = None
    quantidade_minima: int = 0


class PecaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    marca_modelo_compativel: str
    ano_compativel: str
    preco: Decimal
    quantidade_estoque: int
    imagem_url: str | None
    quantidade_minima: int
    criado_em: datetime


def get_use_cases(
    session: AsyncSession = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> PecaUseCases:
    return PecaUseCases(SqlAlchemyPecaRepository(session, embedding_service))


@router.post("", response_model=PecaOut, status_code=201)
async def criar_peca(
    payload: PecaCreate,
    use_cases: PecaUseCases = Depends(get_use_cases),
    # GET é público (catálogo não é dado sensível); POST/PUT/DELETE exigem login.
    _usuario: Usuario = Depends(get_current_user),
) -> Peca:
    peca = Peca(
        id=uuid4(),
        nome=payload.nome,
        marca_modelo_compativel=payload.marca_modelo_compativel,
        ano_compativel=payload.ano_compativel,
        preco=payload.preco,
        quantidade_estoque=payload.quantidade_estoque,
        imagem_url=payload.imagem_url,
        quantidade_minima=payload.quantidade_minima,
        criado_em=datetime.now(timezone.utc),
    )
    return await use_cases.criar(peca)


@router.get("", response_model=list[PecaOut])
async def listar_pecas(use_cases: PecaUseCases = Depends(get_use_cases)) -> list[Peca]:
    return await use_cases.listar()


@router.get("/{peca_id}", response_model=PecaOut)
async def buscar_peca(
    peca_id: UUID, use_cases: PecaUseCases = Depends(get_use_cases)
) -> Peca:
    peca = await use_cases.buscar_por_id(peca_id)
    if peca is None:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    return peca


@router.put("/{peca_id}", response_model=PecaOut)
async def atualizar_peca(
    peca_id: UUID,
    payload: PecaUpdate,
    use_cases: PecaUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Peca:
    existente = await use_cases.buscar_por_id(peca_id)
    if existente is None:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    peca = Peca(
        id=peca_id,
        nome=payload.nome,
        marca_modelo_compativel=payload.marca_modelo_compativel,
        ano_compativel=payload.ano_compativel,
        preco=payload.preco,
        quantidade_estoque=payload.quantidade_estoque,
        imagem_url=payload.imagem_url,
        quantidade_minima=payload.quantidade_minima,
        criado_em=existente.criado_em,
    )
    atualizada = await use_cases.atualizar(peca)
    if atualizada is None:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    return atualizada


@router.delete("/{peca_id}", status_code=204)
async def excluir_peca(
    peca_id: UUID,
    use_cases: PecaUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> None:
    try:
        excluida = await use_cases.excluir(peca_id)
    except PecaPossuiPedidosError:
        raise HTTPException(
            status_code=409,
            detail="Não é possível excluir: peça possui pedidos vinculados",
        )
    if not excluida:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
