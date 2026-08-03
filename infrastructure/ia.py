from adapters.gemini_adapter import GeminiEmbeddingService
from adapters.groq_adapter import GroqAdapter, GroqClassificador
from application.chat_service import ChatService
from application.classificacao_mensagem_service import ClassificadorDeMensagem
from application.embedding_service import EmbeddingService
from infrastructure.config import settings


# Módulo próprio (não dentro do router) pra testes sobrescreverem uma única
# função via app.dependency_overrides, valendo pra todos os endpoints.
def get_classificador() -> ClassificadorDeMensagem:
    return GroqClassificador(api_key=settings.groq_api_key)


def get_chat_service() -> ChatService:
    return GroqAdapter(api_key=settings.groq_api_key)


def get_embedding_service() -> EmbeddingService:
    return GeminiEmbeddingService(api_key=settings.gemini_api_key)
