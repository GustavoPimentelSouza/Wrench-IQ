from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import ConfiguracaoOficinaORM
from domain.configuracao_oficina import ConfiguracaoOficina

# Sempre a mesma linha (id=1) — a oficina só tem um horário de
# funcionamento, nunca faz sentido ter mais de uma configuração.
_ID_UNICO = 1


def _to_domain(orm: ConfiguracaoOficinaORM) -> ConfiguracaoOficina:
    return ConfiguracaoOficina(
        id=orm.id,
        horario_semana_abertura=orm.horario_semana_abertura,
        horario_semana_fechamento=orm.horario_semana_fechamento,
        horario_sabado_abertura=orm.horario_sabado_abertura,
        horario_sabado_fechamento=orm.horario_sabado_fechamento,
        horario_domingo_abertura=orm.horario_domingo_abertura,
        horario_domingo_fechamento=orm.horario_domingo_fechamento,
    )


class SqlAlchemyConfiguracaoOficinaRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def buscar(self) -> ConfiguracaoOficina | None:
        orm = await self._session.get(ConfiguracaoOficinaORM, _ID_UNICO)
        return _to_domain(orm) if orm else None

    async def salvar(self, configuracao: ConfiguracaoOficina) -> ConfiguracaoOficina:
        orm = await self._session.get(ConfiguracaoOficinaORM, _ID_UNICO)
        if orm is None:
            orm = ConfiguracaoOficinaORM(id=_ID_UNICO)
            self._session.add(orm)
        orm.horario_semana_abertura = configuracao.horario_semana_abertura
        orm.horario_semana_fechamento = configuracao.horario_semana_fechamento
        orm.horario_sabado_abertura = configuracao.horario_sabado_abertura
        orm.horario_sabado_fechamento = configuracao.horario_sabado_fechamento
        orm.horario_domingo_abertura = configuracao.horario_domingo_abertura
        orm.horario_domingo_fechamento = configuracao.horario_domingo_fechamento
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)
