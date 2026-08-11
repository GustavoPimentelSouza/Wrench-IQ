from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from domain.agendamento import Agendamento


class AgendamentoRepository(Protocol):
    async def criar(self, agendamento: Agendamento) -> Agendamento: ...

    # Todos os agendamentos, de todos os clientes — usado pela AgendaPage
    # (visão da oficina inteira). Sem isso, um agendamento criado pela IA
    # via chat ficava invisível pro time, só consultável por cliente.
    async def listar(self) -> list[Agendamento]: ...

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Agendamento]: ...

    # Usado por AgendamentoDisponibilidadeUseCases pra calcular quantas
    # vagas já estão ocupadas num dia, por especialidade.
    async def listar_por_data(self, data: date) -> list[Agendamento]: ...

    # Usado pelo "worker" de no-show (liberar_no_shows) — agendamentos
    # ainda AGENDADO/CONFIRMADO cujo horário já passou da tolerância.
    async def listar_pendentes_antes_de(self, limite: datetime) -> list[Agendamento]: ...

    async def buscar_por_id(self, agendamento_id: UUID) -> Agendamento | None: ...

    async def atualizar(self, agendamento: Agendamento) -> Agendamento | None: ...

    async def excluir(self, agendamento_id: UUID) -> bool: ...
