from datetime import datetime, timezone
from uuid import UUID, uuid4

from application.classificacao_mensagem_service import ClassificadorDeMensagem
from application.mensagem_repository import MensagemRepository
from domain.mensagem import Mensagem


class MensagemUseCases:
    def __init__(
        self, repository: MensagemRepository, classificador: ClassificadorDeMensagem
    ):
        self._repository = repository
        self._classificador = classificador

    async def receber(self, cliente_id: UUID, texto: str) -> Mensagem:
        # Este método é chamado toda vez que uma mensagem de texto chega
        # (hoje, pelos dois endpoints de webhook — /webhook e
        # /webhook/whatsapp — e também pela rota manual /mensagens).
        # A "regra de negócio" inteira do MensagemUseCases é só isso:
        # montar a entidade com id/data novos, usando o classificador
        # injetado (ClassificadorDeMensagem — hoje o GroqClassificador, mas
        # podia ser qualquer implementação) pra decidir a categoria ANTES de
        # persistir. O use case não sabe COMO a classificação funciona por
        # dentro — só chama `.classificar()` e confia no resultado. Isso é o
        # que torna esse caso de uso testável sem custo/latência de IA
        # real: nos testes, injetamos um FakeClassificador no lugar (ver
        # tests/fakes.py).
        categoria = await self._classificador.classificar(texto)
        mensagem = Mensagem(
            id=uuid4(),
            cliente_id=cliente_id,
            texto=texto,
            categoria=categoria,
            criado_em=datetime.now(timezone.utc),
        )
        return await self._repository.criar(mensagem)
