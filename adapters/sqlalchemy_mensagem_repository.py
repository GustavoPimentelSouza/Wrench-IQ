from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import MensagemORM
from domain.mensagem import CategoriaMensagem, Mensagem, MotivoAtendimento


def _to_domain(orm: MensagemORM) -> Mensagem:
    return Mensagem(
        id=orm.id,
        cliente_id=orm.cliente_id,
        texto=orm.texto,
        categoria=CategoriaMensagem(orm.categoria),
        criado_em=orm.criado_em,
        resposta_ia=orm.resposta_ia,
        precisa_atendimento_humano=orm.precisa_atendimento_humano,
        motivo_atendimento=(
            MotivoAtendimento(orm.motivo_atendimento) if orm.motivo_atendimento else None
        ),
        atendimento_resolvido=orm.atendimento_resolvido,
        acao_finalizadora=orm.acao_finalizadora,
        imagem_url=orm.imagem_url,
        ferramentas_chamadas=orm.ferramentas_chamadas.split(",") if orm.ferramentas_chamadas else [],
    )


class SqlAlchemyMensagemRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, mensagem: Mensagem) -> Mensagem:
        orm = MensagemORM(
            id=mensagem.id,
            cliente_id=mensagem.cliente_id,
            texto=mensagem.texto,
            categoria=mensagem.categoria.value,
            criado_em=mensagem.criado_em,
            precisa_atendimento_humano=mensagem.precisa_atendimento_humano,
            motivo_atendimento=(
                mensagem.motivo_atendimento.value if mensagem.motivo_atendimento else None
            ),
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def buscar_por_id(self, mensagem_id: UUID) -> Mensagem | None:
        orm = await self._session.get(MensagemORM, mensagem_id)
        return _to_domain(orm) if orm else None

    async def listar_por_cliente(
        self, cliente_id: UUID, limit: int, desde: datetime | None = None
    ) -> list[Mensagem]:
        query = select(MensagemORM).where(MensagemORM.cliente_id == cliente_id)
        if desde is not None:
            query = query.where(MensagemORM.criado_em >= desde)
        query = query.order_by(MensagemORM.criado_em.desc()).limit(limit)
        result = await self._session.execute(query)
        mensagens = [_to_domain(orm) for orm in result.scalars().all()]
        return list(reversed(mensagens))  # mais antiga primeiro, pra virar histórico

    async def registrar_resposta(
        self,
        mensagem_id: UUID,
        resposta: str,
        acao_finalizadora: str | None = None,
        imagem_url: str | None = None,
        ferramentas_chamadas: list[str] | None = None,
    ) -> None:
        orm = await self._session.get(MensagemORM, mensagem_id)
        if orm is None:
            return
        orm.resposta_ia = resposta
        orm.acao_finalizadora = acao_finalizadora
        orm.imagem_url = imagem_url
        orm.ferramentas_chamadas = ",".join(ferramentas_chamadas) if ferramentas_chamadas else None
        await self._session.commit()

    # orm is None é silencioso (não levanta erro) igual registrar_resposta
    # acima — mesmo padrão já usado no projeto pra "marcar algo que já
    # pode ter sumido" sem quebrar o fluxo de quem chamou.
    async def marcar_precisa_atendimento(
        self, mensagem_id: UUID, motivo: MotivoAtendimento
    ) -> None:
        orm = await self._session.get(MensagemORM, mensagem_id)
        if orm is None:
            return
        orm.precisa_atendimento_humano = True
        orm.motivo_atendimento = motivo.value
        await self._session.commit()

    async def marcar_atendimento_resolvido(self, mensagem_id: UUID) -> None:
        orm = await self._session.get(MensagemORM, mensagem_id)
        if orm is None:
            return
        orm.atendimento_resolvido = True
        await self._session.commit()

    # Os dois filtros juntos (precisa=True E resolvido=False) são o que
    # define "está na fila agora" — resolvido vira True quando o staff
    # já cuidou, sem precisar apagar o registro histórico.
    async def listar_pendentes_atendimento(self) -> list[Mensagem]:
        result = await self._session.execute(
            select(MensagemORM)
            .where(
                MensagemORM.precisa_atendimento_humano.is_(True),
                MensagemORM.atendimento_resolvido.is_(False),
            )
            .order_by(MensagemORM.criado_em.desc())
        )
        return [_to_domain(orm) for orm in result.scalars().all()]
