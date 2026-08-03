from typing import Protocol

from domain.configuracao_oficina import ConfiguracaoOficina


class ConfiguracaoOficinaRepository(Protocol):
    async def buscar(self) -> ConfiguracaoOficina | None: ...

    # "Salvar" em vez de "criar"/"atualizar" separados — é sempre a mesma
    # linha única (upsert), nunca faz sentido ter duas configurações.
    async def salvar(self, configuracao: ConfiguracaoOficina) -> ConfiguracaoOficina: ...
