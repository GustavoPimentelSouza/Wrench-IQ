from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_agendamento_repository import SqlAlchemyAgendamentoRepository
from adapters.sqlalchemy_cliente_repository import SqlAlchemyClienteRepository
from adapters.sqlalchemy_configuracao_oficina_repository import (
    SqlAlchemyConfiguracaoOficinaRepository,
)
from adapters.sqlalchemy_mensagem_repository import SqlAlchemyMensagemRepository
from adapters.sqlalchemy_movimentacao_estoque_repository import (
    SqlAlchemyMovimentacaoEstoqueRepository,
)
from adapters.sqlalchemy_peca_repository import SqlAlchemyPecaRepository
from adapters.sqlalchemy_pedido_repository import SqlAlchemyPedidoRepository
from application.agendamento_use_cases import AgendamentoUseCases
from application.chat_service import ChatService
from application.classificacao_mensagem_service import ClassificadorDeMensagem
from application.configuracao_oficina_use_cases import ConfiguracaoOficinaUseCases
from application.conversa_use_cases import ConversaUseCases
from application.embedding_service import EmbeddingService
from application.mensagem_use_cases import MensagemUseCases
from application.pedido_use_cases import PedidoUseCases
from domain.cliente import Cliente, telefone_valido
from infrastructure.db import get_db
from infrastructure.ia import get_chat_service, get_classificador, get_embedding_service

router = APIRouter()


async def _buscar_ou_criar_cliente(
    cliente_repository: SqlAlchemyClienteRepository, telefone: str, nome: str
) -> Cliente:
    cliente = await cliente_repository.buscar_por_telefone(telefone)
    if cliente is not None:
        return cliente
    return await cliente_repository.criar(
        Cliente(id=uuid4(), nome=nome, telefone=telefone, criado_em=datetime.now(timezone.utc))
    )


class WebhookIn(BaseModel):
    telefone: str
    mensagem: str

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, valor: str) -> str:
        if not telefone_valido(valor):
            raise ValueError(
                "Telefone deve conter só dígitos, entre 10 e 15 caracteres (ex: 5511999999999)"
            )
        return valor


class RespostaOut(BaseModel):
    resposta: str
    ferramentas_chamadas: list[str] = []
    imagem_url: str | None = None


@router.post("/webhook", response_model=RespostaOut)
async def webhook(
    payload: WebhookIn,
    session: AsyncSession = Depends(get_db),
    classificador: ClassificadorDeMensagem = Depends(get_classificador),
    chat_service: ChatService = Depends(get_chat_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> RespostaOut:
    cliente_repository = SqlAlchemyClienteRepository(session)
    # Cliente novo via WhatsApp — nome fica como o telefone até ser atualizado depois.
    cliente = await _buscar_ou_criar_cliente(cliente_repository, payload.telefone, payload.telefone)

    mensagem_use_cases = MensagemUseCases(SqlAlchemyMensagemRepository(session), classificador)
    # Buscado ANTES de criar a mensagem atual — senão ela apareceria duas
    # vezes (uma no histórico, outra como a mensagem da vez).
    historico = await mensagem_use_cases.listar_recentes(cliente.id)
    mensagem = await mensagem_use_cases.receber(cliente.id, payload.mensagem)

    peca_repository = SqlAlchemyPecaRepository(session, embedding_service)
    pedido_use_cases = PedidoUseCases(
        SqlAlchemyPedidoRepository(session),
        peca_repository,
        SqlAlchemyMovimentacaoEstoqueRepository(session),
    )
    configuracao_oficina_use_cases = ConfiguracaoOficinaUseCases(
        SqlAlchemyConfiguracaoOficinaRepository(session)
    )
    agendamento_use_cases = AgendamentoUseCases(SqlAlchemyAgendamentoRepository(session))
    conversa_use_cases = ConversaUseCases(
        chat_service,
        peca_repository,
        pedido_use_cases,
        configuracao_oficina_use_cases,
        agendamento_use_cases,
    )
    resultado = await conversa_use_cases.responder(
        payload.mensagem, cliente.id, mensagem.categoria, historico
    )
    await mensagem_use_cases.registrar_resposta(mensagem.id, resultado.texto)
    if resultado.precisa_atendimento_humano:
        await mensagem_use_cases.marcar_precisa_atendimento(mensagem.id)

    return RespostaOut(
        resposta=resultado.texto,
        ferramentas_chamadas=resultado.ferramentas_chamadas,
        imagem_url=resultado.imagem_url,
    )


class EvolutionWebhookKey(BaseModel):
    remoteJid: str
    fromMe: bool = False
    id: str | None = None


class EvolutionWebhookMessage(BaseModel):
    conversation: str | None = None
    extendedTextMessage: dict[str, Any] | None = None
    audioMessage: dict[str, Any] | None = None
    imageMessage: dict[str, Any] | None = None


class EvolutionWebhookData(BaseModel):
    key: EvolutionWebhookKey
    pushName: str | None = None
    message: EvolutionWebhookMessage
    messageType: str


class EvolutionWebhookIn(BaseModel):
    event: str
    instance: str
    data: EvolutionWebhookData


class WhatsappWebhookOut(BaseModel):
    status: str
    tipo: str


def _extrair_telefone(remote_jid: str) -> str:
    return remote_jid.split("@")[0]


def _extrair_texto(mensagem: EvolutionWebhookMessage) -> str | None:
    if mensagem.conversation:
        return mensagem.conversation
    if mensagem.extendedTextMessage:
        texto = mensagem.extendedTextMessage.get("text")
        if texto:
            return texto
    return None


@router.post("/webhook/whatsapp", response_model=WhatsappWebhookOut)
async def webhook_whatsapp(
    payload: EvolutionWebhookIn,
    session: AsyncSession = Depends(get_db),
    classificador: ClassificadorDeMensagem = Depends(get_classificador),
) -> WhatsappWebhookOut:
    dados = payload.data

    if dados.key.fromMe:
        # Eco de mensagem enviada pelo próprio número do negócio — não é
        # input de cliente, não deve virar triagem.
        return WhatsappWebhookOut(status="ignorado", tipo=dados.messageType)

    texto = _extrair_texto(dados.message)
    if texto is None:
        # Áudio e imagem chegam aqui reconhecidos, mas ainda não passam por
        # transcrição/visão — essa etapa (multimodalidade) vem depois de tool
        # calling e RAG na ordem incremental do projeto (ver CLAUDE.md).
        return WhatsappWebhookOut(status="recebido_sem_processamento", tipo=dados.messageType)

    telefone = _extrair_telefone(dados.key.remoteJid)
    if not telefone_valido(telefone):
        raise HTTPException(
            status_code=400, detail="remoteJid não corresponde a um telefone válido"
        )

    cliente_repository = SqlAlchemyClienteRepository(session)
    cliente = await _buscar_ou_criar_cliente(
        cliente_repository, telefone, dados.pushName or telefone
    )

    mensagem_use_cases = MensagemUseCases(SqlAlchemyMensagemRepository(session), classificador)
    await mensagem_use_cases.receber(cliente.id, texto)

    return WhatsappWebhookOut(status="processado", tipo=dados.messageType)
