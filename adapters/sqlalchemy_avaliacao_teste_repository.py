from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_avaliacao_teste import AvaliacaoTesteORM
from adapters.orm_models import ClienteORM, MensagemORM
from application.avaliacao_teste_repository import ResumoConversaTeste
from domain.avaliacao_teste import AvaliacaoTeste, ResultadoAvaliacao

# Telefone que o botão "Nova conversa" do simulador gera: "5599" + 8 dígitos
# (ver gerarTelefoneDeTeste no ChatSimuladorPage). Deixa de fora clientes
# reais e os de testes automáticos antigos (telefones de 11/14/15 dígitos).
_PREFIXO_SIMULADOR = "5599"
_TAMANHO_TELEFONE_SIMULADOR = 12


def _to_domain(orm: AvaliacaoTesteORM) -> AvaliacaoTeste:
    return AvaliacaoTeste(
        id=orm.id,
        cliente_id=orm.cliente_id,
        resultado=ResultadoAvaliacao(orm.resultado),
        comentario=orm.comentario,
        criado_em=orm.criado_em,
        atualizado_em=orm.atualizado_em,
    )


class SqlAlchemyAvaliacaoTesteRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def buscar_por_cliente(self, cliente_id: UUID) -> AvaliacaoTeste | None:
        result = await self._session.execute(
            select(AvaliacaoTesteORM).where(AvaliacaoTesteORM.cliente_id == cliente_id)
        )
        orm = result.scalar_one_or_none()
        return _to_domain(orm) if orm else None

    async def salvar(self, avaliacao: AvaliacaoTeste) -> AvaliacaoTeste:
        # merge = insert se o id é novo, update se já existe.
        orm = await self._session.merge(
            AvaliacaoTesteORM(
                id=avaliacao.id,
                cliente_id=avaliacao.cliente_id,
                resultado=avaliacao.resultado.value,
                comentario=avaliacao.comentario,
                criado_em=avaliacao.criado_em,
                atualizado_em=avaliacao.atualizado_em,
            )
        )
        await self._session.commit()
        return _to_domain(orm)

    async def listar_conversas(self) -> list[ResumoConversaTeste]:
        inicio = func.min(MensagemORM.criado_em)
        query = (
            select(
                ClienteORM.id, ClienteORM.telefone, inicio,
                func.max(MensagemORM.criado_em), func.count(MensagemORM.id),
                AvaliacaoTesteORM.resultado, AvaliacaoTesteORM.comentario,
            )
            .join(MensagemORM, MensagemORM.cliente_id == ClienteORM.id)
            # outer join: conversa sem avaliação também aparece (aba "Não avaliadas").
            .outerjoin(AvaliacaoTesteORM, AvaliacaoTesteORM.cliente_id == ClienteORM.id)
            .where(ClienteORM.telefone.startswith(_PREFIXO_SIMULADOR))
            .where(func.length(ClienteORM.telefone) == _TAMANHO_TELEFONE_SIMULADOR)
            .group_by(ClienteORM.id, AvaliacaoTesteORM.id)
            .order_by(inicio.desc())
        )
        result = await self._session.execute(query)
        return [
            ResumoConversaTeste(
                cliente_id=linha[0], telefone=linha[1], inicio=linha[2], fim=linha[3],
                total_mensagens=linha[4],
                resultado=ResultadoAvaliacao(linha[5]) if linha[5] else None,
                comentario=linha[6],
            )
            for linha in result.all()
        ]
