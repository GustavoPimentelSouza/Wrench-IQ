from typing import Protocol
from uuid import UUID

from domain.cliente import Cliente


class ClientePossuiProtocolosError(Exception):
    """Levantado ao tentar excluir um cliente que ainda tem protocolos vinculados."""


# Este é o arquivo "modelo" pra entender TODOS os outros *_repository.py do
# projeto — eles seguem exatamente esse padrão, só trocando a entidade.
#
# `Protocol` (de typing) é diferente de uma classe abstrata (ABC): não
# precisa herdar dele explicitamente pra "implementar" a interface — basta
# a classe ter os métodos com a assinatura certa (duck typing verificado
# estaticamente pelo type checker). É por isso que
# adapters/sqlalchemy_cliente_repository.py não escreve
# "class SqlAlchemyClienteRepository(ClienteRepository)" — não precisa.
#
# Repara também: essa interface não sabe NADA de SQL, sessão de banco,
# HTTP. É só "o que dá pra fazer com um Cliente", em português claro. Quem
# decide COMO fazer (Postgres? outro banco? um mock em memória pra teste?)
# é responsabilidade de quem implementa isso lá em adapters/.
class ClienteRepository(Protocol):
    async def criar(self, cliente: Cliente) -> Cliente: ...

    async def listar(self) -> list[Cliente]: ...

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None: ...

    # Usado no webhook do WhatsApp — o telefone é o identificador natural
    # de "quem está mandando mensagem", já que não tem login/senha ali.
    async def buscar_por_telefone(self, telefone: str) -> Cliente | None: ...

    async def atualizar(self, cliente: Cliente) -> Cliente | None: ...

    # Pode levantar ClientePossuiProtocolosError (definida acima) se o banco
    # recusar por causa de uma FK com ondelete=RESTRICT — ex: cliente que
    # ainda tem protocolo/veículo/mensagem vinculado não pode ser apagado.
    async def excluir(self, cliente_id: UUID) -> bool: ...
