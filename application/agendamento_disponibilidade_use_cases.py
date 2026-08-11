from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID, uuid4

from application.agendamento_repository import AgendamentoRepository
from application.lista_espera_repository import ListaEsperaRepository
from application.notificacao_use_cases import NotificacaoUseCases
from application.usuario_repository import UsuarioRepository
from domain.agendamento import Agendamento, StatusAgendamento
from domain.configuracao_oficina import ConfiguracaoOficina
from domain.especialidade import Especialidade, especialidades_para_disponibilidade
from domain.lista_espera_agendamento import ListaEsperaAgendamento
from domain.notificacao import Notificacao, TipoNotificacao

_DURACAO_SLOT_MINUTOS = 60
# Nunca deixa a busca de "próxima data" rodar pra sempre se a oficina
# realmente não tiver vaga tão cedo — depois disso, a conversa deve oferecer
# a lista de espera em vez de continuar varrendo o calendário.
_HORIZONTE_BUSCA_DIAS = 30
# Tempo que o primeiro da lista de espera tem pra confirmar antes da vaga
# passar pro próximo — mensagem de POST /agendamentos/lista-espera.
_PRAZO_CONFIRMACAO_MINUTOS = 30


@dataclass
class DisponibilidadeResultado:
    disponivel_na_data: bool
    horarios_disponiveis: list[datetime] = field(default_factory=list)
    # Regra de negócio (item 5): nunca responder só "sem horário" — isso é
    # resposta de porta fechada e empurra o cliente pra procurar a
    # concorrência ali mesmo. Toda vez que disponivel_na_data é False, esse
    # caso de uso já busca e devolve a próxima data com vaga (dentro do
    # horizonte de busca), garantindo uma saída real na conversa: aceitar a
    # alternativa ou entrar na lista de espera. Só fica None no caso
    # genuinamente sem solução — zero mecânico qualificado pra essa
    # especialidade não é "sem horário agora", é "não tem quem atenda",
    # problema estrutural de quadro, não de agenda.
    proxima_data_disponivel: date | None = None
    proximos_horarios: list[datetime] = field(default_factory=list)


class AgendamentoDisponibilidadeUseCases:
    def __init__(
        self,
        agendamento_repository: AgendamentoRepository,
        usuario_repository: UsuarioRepository,
        lista_espera_repository: ListaEsperaRepository,
        notificacoes: NotificacaoUseCases,
    ):
        self._agendamentos = agendamento_repository
        self._usuarios = usuario_repository
        self._lista_espera = lista_espera_repository
        self._notificacoes = notificacoes

    async def consultar_disponibilidade(
        self,
        especialidades: list[Especialidade],
        data_desejada: date,
        configuracao: ConfiguracaoOficina,
    ) -> DisponibilidadeResultado:
        especialidades_capacidade = especialidades_para_disponibilidade(especialidades)
        capacidade = len(
            await self._usuarios.listar_mecanicos_por_especialidade(especialidades_capacidade)
        )

        horarios = await self._horarios_livres(
            data_desejada, especialidades_capacidade, capacidade, configuracao
        )
        if horarios:
            return DisponibilidadeResultado(True, horarios_disponiveis=horarios)
        if capacidade == 0:
            return DisponibilidadeResultado(False)

        for offset in range(1, _HORIZONTE_BUSCA_DIAS + 1):
            data_candidata = data_desejada + timedelta(days=offset)
            candidatos = await self._horarios_livres(
                data_candidata, especialidades_capacidade, capacidade, configuracao
            )
            if candidatos:
                return DisponibilidadeResultado(
                    False, proxima_data_disponivel=data_candidata, proximos_horarios=candidatos
                )
        return DisponibilidadeResultado(False)

    async def _horarios_livres(
        self,
        data: date,
        especialidades_capacidade: list[Especialidade],
        capacidade: int,
        configuracao: ConfiguracaoOficina,
    ) -> list[datetime]:
        if capacidade == 0:
            return []
        abertura, fechamento = _horario_do_dia(data, configuracao)
        if abertura is None or fechamento is None:
            return []

        agendamentos_do_dia = await self._agendamentos.listar_por_data(data)
        livres = []
        horario = datetime.combine(data, abertura, tzinfo=timezone.utc)
        limite = datetime.combine(data, fechamento, tzinfo=timezone.utc)
        while horario + timedelta(minutes=_DURACAO_SLOT_MINUTOS) <= limite:
            # Capacidade por CONTAGEM, não por mecânico específico atribuído
            # (Agendamento não tem mecanico_id) — um slot está livre se
            # menos agendamentos dessa especialidade já ocupam ele do que
            # existem mecânicos qualificados pra cobri-la.
            ocupados = sum(
                1
                for agendamento in agendamentos_do_dia
                if agendamento.data_hora == horario
                and set(especialidades_para_disponibilidade(agendamento.especialidades))
                & set(especialidades_capacidade)
            )
            if ocupados < capacidade:
                livres.append(horario)
            horario += timedelta(minutes=_DURACAO_SLOT_MINUTOS)
        return livres

    async def entrar_na_lista_de_espera(
        self, cliente_id: UUID, especialidade: Especialidade
    ) -> ListaEsperaAgendamento:
        return await self._lista_espera.criar(
            ListaEsperaAgendamento(
                id=uuid4(),
                cliente_id=cliente_id,
                especialidade=especialidade,
                criado_em=datetime.now(timezone.utc),
            )
        )

    # Mesmo padrão de PedidoUseCases.cancelar_expirados / POST
    # /pedidos/expirar-retiradas: não existe worker de fila de verdade
    # rodando em background ainda — um cron externo bate nesse endpoint
    # periodicamente, e esse método faz a varredura de uma vez.
    async def liberar_no_shows(self, configuracao: ConfiguracaoOficina) -> list[Agendamento]:
        limite = datetime.now(timezone.utc) - timedelta(
            minutes=configuracao.tolerancia_no_show_minutos
        )
        pendentes = await self._agendamentos.listar_pendentes_antes_de(limite)
        liberados = []
        for agendamento in pendentes:
            agendamento.status = StatusAgendamento.NAO_COMPARECEU
            atualizado = await self._agendamentos.atualizar(agendamento)
            assert atualizado is not None
            liberados.append(atualizado)
            await self._notificar_proximo_da_espera(atualizado.especialidades)
        return liberados

    # Chamado por quem detecta o cancelamento (ver PUT /agendamentos/{id})
    # — mora aqui, não em AgendamentoUseCases, porque é especificamente
    # sobre lista de espera/capacidade, não sobre o CRUD básico do
    # agendamento em si.
    async def notificar_cancelamento(self, agendamento: Agendamento) -> None:
        await self._notificar_proximo_da_espera(agendamento.especialidades)

    async def _notificar_proximo_da_espera(self, especialidades: list[Especialidade]) -> None:
        for especialidade in especialidades_para_disponibilidade(especialidades):
            proximo = await self._lista_espera.buscar_primeiro_pendente(especialidade)
            if proximo is None:
                continue
            await self._lista_espera.marcar_atendido(proximo.id)
            await self._notificacoes.criar(
                Notificacao(
                    id=uuid4(),
                    cliente_id=proximo.cliente_id,
                    tipo=TipoNotificacao.LISTA_ESPERA_VAGA_DISPONIVEL,
                    mensagem=(
                        f"Abriu uma vaga pra {especialidade.value}! Responda "
                        f"em até {_PRAZO_CONFIRMACAO_MINUTOS} minutos pra "
                        "confirmar, senão ela passa pro próximo da fila."
                    ),
                    criado_em=datetime.now(timezone.utc),
                )
            )


def _horario_do_dia(
    data: date, configuracao: ConfiguracaoOficina
) -> tuple[time | None, time | None]:
    dia_semana = data.weekday()  # 0=segunda ... 5=sábado, 6=domingo
    if dia_semana == 5:
        return configuracao.horario_sabado_abertura, configuracao.horario_sabado_fechamento
    if dia_semana == 6:
        return configuracao.horario_domingo_abertura, configuracao.horario_domingo_fechamento
    return configuracao.horario_semana_abertura, configuracao.horario_semana_fechamento
