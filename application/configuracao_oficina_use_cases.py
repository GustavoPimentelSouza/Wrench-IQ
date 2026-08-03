from datetime import time

from application.configuracao_oficina_repository import ConfiguracaoOficinaRepository
from domain.configuracao_oficina import ConfiguracaoOficina

# Só existe até a oficina configurar algo diferente pela tela — evita a IA
# ficar sem resposta (ou pior, inventando horário) antes do primeiro acesso
# às configurações.
_PADRAO = ConfiguracaoOficina(
    id=1,
    horario_semana_abertura=time(8, 0),
    horario_semana_fechamento=time(19, 0),
    horario_sabado_abertura=time(8, 0),
    horario_sabado_fechamento=time(18, 0),
    horario_domingo_abertura=time(8, 0),
    horario_domingo_fechamento=time(12, 0),
)


class ConfiguracaoOficinaUseCases:
    def __init__(self, repository: ConfiguracaoOficinaRepository):
        self._repository = repository

    async def buscar(self) -> ConfiguracaoOficina:
        configuracao = await self._repository.buscar()
        return configuracao if configuracao is not None else _PADRAO

    async def atualizar(self, configuracao: ConfiguracaoOficina) -> ConfiguracaoOficina:
        _validar_periodo(configuracao.horario_semana_abertura, configuracao.horario_semana_fechamento)
        _validar_periodo(configuracao.horario_sabado_abertura, configuracao.horario_sabado_fechamento)
        _validar_periodo(configuracao.horario_domingo_abertura, configuracao.horario_domingo_fechamento)
        return await self._repository.salvar(configuracao)


def _validar_periodo(abertura: time | None, fechamento: time | None) -> None:
    # Um dia fechado tem os dois None — só é inválido ter só um dos dois.
    if (abertura is None) != (fechamento is None):
        raise ValueError("Horário de abertura e fechamento devem ser preenchidos juntos")
    if abertura is not None and fechamento is not None and abertura >= fechamento:
        raise ValueError("Horário de abertura deve ser antes do fechamento")
