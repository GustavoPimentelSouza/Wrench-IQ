import uuid
from datetime import date, datetime, timezone

from adapters.orm_models import ClienteORM
from adapters.sqlalchemy_protocolo_repository import SqlAlchemyProtocoloRepository
from adapters.sqlalchemy_reclassificacao_repository import SqlAlchemyReclassificacaoRepository
from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from application.protocolo_use_cases import ProtocoloUseCases
from domain.especialidade import Especialidade
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
