from adapters.groq_adapter import GroqClassificador
from application.classificacao_mensagem_service import ClassificadorDeMensagem
from infrastructure.config import settings


# Fica num módulo próprio (não dentro de cada router) porque é usado por
# mais de um lugar (infrastructure/routers/mensagens.py e
# infrastructure/routers/webhook.py) — definir em um lugar só significa que
# os testes precisam sobrescrever essa ÚNICA função (via
# app.dependency_overrides) pra trocar por um FakeClassificador em todos os
# endpoints de uma vez, em vez de precisar lembrar de sobrescrever em cada
# router separadamente.
def get_classificador() -> ClassificadorDeMensagem:
    return GroqClassificador(api_key=settings.groq_api_key)
