from uuid import UUID

from application.cliente_repository import ClienteRepository
from domain.cliente import Cliente


# Este é o "use case" mais simples do projeto — e por isso o melhor pra
# entender o padrão que se repete em Peca/Protocolo/Veiculo/Agendamento.
#
# Um UseCases não sabe nada de HTTP nem de SQL — só recebe um Repository
# (a interface Protocol, não a implementação concreta) no construtor, e
# delega quase tudo pra ele. Pra Cliente, praticamente não tem regra de
# negócio própria — é "passa reto" na maioria dos métodos. Compare com
# PedidoUseCases (bem mais complexo) pra ver a diferença entre um use case
# que só orquestra e um que de fato tem lógica.
class ClienteUseCases:
    def __init__(self, repository: ClienteRepository):
        # O "_" na frente é convenção Python pra "privado" (não é privado de
        # verdade, é só sinalização — nada impede acessar de fora, mas
        # avisa "não deveria").
        self._repository = repository

    async def criar(self, cliente: Cliente) -> Cliente:
        return await self._repository.criar(cliente)

    async def listar(self) -> list[Cliente]:
        return await self._repository.listar()

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None:
        return await self._repository.buscar_por_id(cliente_id)

    async def buscar_por_telefone(self, telefone: str) -> Cliente | None:
        return await self._repository.buscar_por_telefone(telefone)

    async def atualizar(self, cliente: Cliente) -> Cliente | None:
        # Esse "buscar antes de atualizar" é o único pedaço de lógica real
        # aqui: confirma que o cliente existe ANTES de tentar atualizar,
        # devolvendo None (que o router converte em HTTP 404) em vez de
        # deixar o banco reclamar com um erro mais confuso. Esse mesmo
        # padrão se repete em quase todo *_use_cases.py do projeto.
        existente = await self._repository.buscar_por_id(cliente.id)
        if existente is None:
            return None
        return await self._repository.atualizar(cliente)

    async def excluir(self, cliente_id: UUID) -> bool:
        return await self._repository.excluir(cliente_id)
