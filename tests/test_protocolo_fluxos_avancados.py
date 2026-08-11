import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from adapters.orm_models import ClienteORM
from adapters.sqlalchemy_item_adicional_repository import SqlAlchemyItemAdicionalRepository
from adapters.sqlalchemy_notificacao_repository import SqlAlchemyNotificacaoRepository
from adapters.sqlalchemy_protocolo_repository import SqlAlchemyProtocoloRepository
from adapters.sqlalchemy_reclassificacao_repository import SqlAlchemyReclassificacaoRepository
from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from application.item_adicional_use_cases import ItemAdicionalUseCases
from application.notificacao_use_cases import NotificacaoUseCases
from application.protocolo_use_cases import ProtocoloUseCases
from domain.especialidade import Especialidade
from domain.item_adicional_protocolo import StatusItemAdicional
from domain.protocolo import Protocolo, StatusProtocolo
from tests.conftest import TestSessionLocal


async def _criar_cliente() -> uuid.UUID:
    cliente_id = uuid.uuid4()
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"
    async with TestSessionLocal() as session:
        session.add(ClienteORM(id=cliente_id, nome="Cliente teste", telefone=telefone))
        await session.commit()
    return cliente_id


def _protocolo_use_cases(session) -> ProtocoloUseCases:
    return ProtocoloUseCases(
        SqlAlchemyProtocoloRepository(session),
        SqlAlchemyUsuarioRepository(session),
        SqlAlchemyReclassificacaoRepository(session),
    )


def _item_adicional_use_cases(session) -> ItemAdicionalUseCases:
    return ItemAdicionalUseCases(
        SqlAlchemyItemAdicionalRepository(session),
        SqlAlchemyProtocoloRepository(session),
        NotificacaoUseCases(SqlAlchemyNotificacaoRepository(session)),
    )


async def _criar_protocolo_em_execucao(session, cliente_id: uuid.UUID) -> Protocolo:
    protocolo = await _protocolo_use_cases(session).criar(
        Protocolo(
            id=uuid.uuid4(),
            cliente_id=cliente_id,
            veiculo="Onix 2022",
            categoria="revisao",
            status=StatusProtocolo.AGUARDANDO_APROVACAO,
            criado_em=datetime.now(timezone.utc),
            especialidades=[Especialidade.MECANICA_GERAL],
        )
    )
    protocolo.valor_orcamento = Decimal("300.00")
    await SqlAlchemyProtocoloRepository(session).atualizar(protocolo)
    return await _protocolo_use_cases(session).aprovar(protocolo.id)


async def test_item_adicional_aprovado_retoma_execucao_com_valor_atualizado():
    cliente_id = await _criar_cliente()
    async with TestSessionLocal() as session:
        protocolo = await _criar_protocolo_em_execucao(session, cliente_id)
        assert protocolo.status == StatusProtocolo.EM_EXECUCAO
        valor_original = protocolo.valor_orcamento

        item_use_cases = _item_adicional_use_cases(session)
        item = await item_use_cases.registrar(
            protocolo.id, "Bomba d'água furada", Decimal("150.00")
        )
        assert item.status == StatusItemAdicional.PENDENTE

        protocolo_bloqueado = await _protocolo_use_cases(session).buscar_por_id(protocolo.id)
        assert protocolo_bloqueado.status == StatusProtocolo.AGUARDANDO_APROVACAO_ADICIONAL

        # Item adicional dispara notificação pro cliente decidir (mesma
        # infra reaproveitada pela lista de espera — ver domain/notificacao.py).
        notificacoes = await NotificacaoUseCases(
            SqlAlchemyNotificacaoRepository(session)
        ).listar_pendentes()
        assert any(n.cliente_id == cliente_id for n in notificacoes)

        item_aprovado = await item_use_cases.aprovar(item.id)
        assert item_aprovado.status == StatusItemAdicional.APROVADO

        protocolo_final = await _protocolo_use_cases(session).buscar_por_id(protocolo.id)
        assert protocolo_final.status == StatusProtocolo.EM_EXECUCAO
        assert protocolo_final.valor_orcamento == valor_original + Decimal("150.00")


async def test_item_adicional_recusado_conclui_com_escopo_original():
    cliente_id = await _criar_cliente()
    async with TestSessionLocal() as session:
        protocolo = await _criar_protocolo_em_execucao(session, cliente_id)
        valor_original = protocolo.valor_orcamento

        item_use_cases = _item_adicional_use_cases(session)
        item = await item_use_cases.registrar(
            protocolo.id, "Troca de amortecedor", Decimal("400.00")
        )

        item_recusado = await item_use_cases.recusar(item.id)
        assert item_recusado.status == StatusItemAdicional.RECUSADO

        protocolo_final = await _protocolo_use_cases(session).buscar_por_id(protocolo.id)
        # Concluído (não fica travado) e SEM o valor do item recusado somado.
        assert protocolo_final.status == StatusProtocolo.PRONTO
        assert protocolo_final.valor_orcamento == valor_original


async def test_reclassificar_especialidade_registra_originais_e_finais():
    cliente_id = await _criar_cliente()
    async with TestSessionLocal() as session:
        protocolo_use_cases = _protocolo_use_cases(session)
        protocolo = await protocolo_use_cases.criar(
            Protocolo(
                id=uuid.uuid4(),
                cliente_id=cliente_id,
                veiculo="HB20 2021",
                categoria="dano_estrutural",
                status=StatusProtocolo.AGUARDANDO_APROVACAO,
                criado_em=datetime.now(timezone.utc),
                especialidades=[Especialidade.FUNILARIA_PINTURA],
            )
        )

        atualizado = await protocolo_use_cases.reclassificar_especialidade(
            protocolo.id, [Especialidade.ELETRICA, Especialidade.MECANICA_GERAL]
        )
        assert set(atualizado.especialidades) == {
            Especialidade.ELETRICA,
            Especialidade.MECANICA_GERAL,
        }

        hoje = date.today()
        reclassificacoes = await SqlAlchemyReclassificacaoRepository(session).listar_por_periodo(
            hoje, hoje
        )
        registro = next(r for r in reclassificacoes if r.protocolo_id == protocolo.id)
        assert registro.especialidades_originais == [Especialidade.FUNILARIA_PINTURA]
        assert set(registro.especialidades_finais) == {
            Especialidade.ELETRICA,
            Especialidade.MECANICA_GERAL,
        }
