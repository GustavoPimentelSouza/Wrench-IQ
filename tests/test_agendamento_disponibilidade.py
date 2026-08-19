import uuid
from datetime import date, datetime, time, timedelta, timezone

from adapters.orm_models import ClienteORM
from adapters.seguranca import criar_hash_senha
from adapters.sqlalchemy_agendamento_repository import SqlAlchemyAgendamentoRepository
from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from application.agendamento_disponibilidade_use_cases import AgendamentoDisponibilidadeUseCases
from domain.agendamento import Agendamento, StatusAgendamento
from domain.configuracao_oficina import ConfiguracaoOficina
from domain.especialidade import Especialidade
from domain.usuario import PapelUsuario, Usuario
from tests.conftest import TestSessionLocal

_CONFIGURACAO = ConfiguracaoOficina(
    id=1,
    nome_empresa="Oficina teste",
    horario_semana_abertura=time(8, 0),
    horario_semana_fechamento=time(19, 0),
    horario_sabado_abertura=None,
    horario_sabado_fechamento=None,
    horario_domingo_abertura=None,
    horario_domingo_fechamento=None,
    tolerancia_no_show_minutos=20,
)


def _proxima_segunda() -> date:
    # Estritamente no futuro (mesmo se hoje já for segunda) — garante que
    # nenhum slot do dia já tenha passado por causa da hora atual.
    hoje = date.today()
    dias_ate_segunda = (7 - hoje.weekday()) % 7 or 7
    return hoje + timedelta(days=dias_ate_segunda)


async def _criar_cliente() -> uuid.UUID:
    cliente_id = uuid.uuid4()
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"
    async with TestSessionLocal() as session:
        session.add(ClienteORM(id=cliente_id, nome="Cliente teste", telefone=telefone))
        await session.commit()
    return cliente_id


async def _criar_mecanico(especialidades: list[Especialidade]) -> None:
    usuario = Usuario(
        id=uuid.uuid4(),
        nome="Mecânico teste",
        email=f"{uuid.uuid4()}@teste.com",
        senha_hash=criar_hash_senha("senha123"),
        papel=PapelUsuario.MECANICO,
        ativo=True,
        criado_em=datetime.now(timezone.utc),
        especialidades=especialidades,
    )
    async with TestSessionLocal() as session:
        await SqlAlchemyUsuarioRepository(session).criar(usuario)


def _use_cases(session) -> AgendamentoDisponibilidadeUseCases:
    return AgendamentoDisponibilidadeUseCases(
        SqlAlchemyAgendamentoRepository(session),
        SqlAlchemyUsuarioRepository(session),
    )


async def test_indefinido_conta_como_mecanica_geral_na_disponibilidade():
    await _criar_mecanico([Especialidade.MECANICA_GERAL])
    data = _proxima_segunda()

    async with TestSessionLocal() as session:
        resultado = await _use_cases(session).consultar_disponibilidade(
            [Especialidade.INDEFINIDO], data, _CONFIGURACAO
        )

    assert resultado.disponivel_na_data is True
    assert resultado.horarios_disponiveis


async def test_disponibilidade_sem_vaga_sempre_traz_proxima_data():
    await _criar_mecanico([Especialidade.ELETRICA])
    data = _proxima_segunda()
    cliente_id = await _criar_cliente()

    async with TestSessionLocal() as session:
        repository = SqlAlchemyAgendamentoRepository(session)
        # Descobre a capacidade DE VERDADE (nº de mecânicos de elétrica já
        # cadastrados no banco de teste, que é compartilhado entre testes
        # do arquivo inteiro) em vez de assumir "1" — assim o teste não
        # quebra se outro teste já tiver criado mecânico de elétrica antes.
        capacidade = len(
            await SqlAlchemyUsuarioRepository(session).listar_mecanicos_por_especialidade(
                [Especialidade.ELETRICA]
            )
        )
        assert capacidade >= 1

        # Lota TODOS os slots do dia (08h às 18h, de hora em hora) com
        # `capacidade` agendamentos cada, pra forçar "sem vaga" na data
        # desejada de propósito.
        horario = datetime.combine(data, time(8, 0), tzinfo=timezone.utc)
        limite = datetime.combine(data, time(19, 0), tzinfo=timezone.utc)
        while horario < limite:
            for _ in range(capacidade):
                await repository.criar(
                    Agendamento(
                        id=uuid.uuid4(),
                        cliente_id=cliente_id,
                        data_hora=horario,
                        status=StatusAgendamento.AGENDADO,
                        criado_em=datetime.now(timezone.utc),
                        especialidades=[Especialidade.ELETRICA],
                    )
                )
            horario += timedelta(hours=1)

        resultado = await _use_cases(session).consultar_disponibilidade(
            [Especialidade.ELETRICA], data, _CONFIGURACAO
        )

    assert resultado.disponivel_na_data is False
    # Regra de negócio: nunca "sem horário" sozinho — sempre com a próxima
    # data disponível junto (terça, mesmo mecânico, ainda sem agendamento).
    assert resultado.proxima_data_disponivel == data + timedelta(days=1)
    assert resultado.proximos_horarios
