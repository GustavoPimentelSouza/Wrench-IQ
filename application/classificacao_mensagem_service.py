from typing import Protocol

from domain.mensagem import CategoriaMensagem


# Interface pra "decidir a categoria de uma mensagem de texto". Antes essa
# lógica vivia dentro de domain/mensagem.py como uma função pura (palavra-
# chave); agora que a classificação depende de uma chamada de IA (rede,
# chave de API, latência), ela não pode mais morar no domain — domain não
# pode depender de nada externo. A interface muda de lugar, mas o conceito
# de negócio (Mensagem, CategoriaMensagem) continua lá.
#
# Implementada hoje por adapters/groq_adapter.py (GroqClassificador). O
# caso de uso (application/mensagem_use_cases.py) só conhece esta interface
# — nunca importa Groq/OpenAI diretamente, então trocar de provedor de IA
# no futuro não exige mudar o use case, só escrever outro adapter.
class ClassificadorDeMensagem(Protocol):
    async def classificar(self, texto: str) -> CategoriaMensagem: ...
