from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_cliente_repository import SqlAlchemyClienteRepository
from adapters.sqlalchemy_mensagem_repository import SqlAlchemyMensagemRepository
from application.classificacao_mensagem_service import ClassificadorDeMensagem
from application.mensagem_use_cases import MensagemUseCases
from domain.cliente import Cliente, telefone_valido
from infrastructure.db import get_db
from infrastructure.ia import get_classificador

router = APIRouter()


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


@router.post("/webhook", response_model=RespostaOut)
async def webhook(
    payload: WebhookIn,
    session: AsyncSession = Depends(get_db),
    classificador: ClassificadorDeMensagem = Depends(get_classificador),
) -> RespostaOut:
    cliente_repository = SqlAlchemyClienteRepository(session)
    cliente = await cliente_repository.buscar_por_telefone(payload.telefone)
    if cliente is None:
        # Cliente novo via WhatsApp — nome fica como o telefone até ser
        # atualizado depois (pelo staff, ou futuramente pela própria IA).
        cliente = await cliente_repository.criar(
            Cliente(
                id=uuid4(),
                nome=payload.telefone,
                telefone=payload.telefone,
                criado_em=datetime.now(timezone.utc),
            )
        )

    mensagem_use_cases = MensagemUseCases(SqlAlchemyMensagemRepository(session), classificador)
    await mensagem_use_cases.receber(cliente.id, payload.mensagem)

    return RespostaOut(resposta=f"recebi sua mensagem: {payload.mensagem}")


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
    cliente = await cliente_repository.buscar_por_telefone(telefone)
    if cliente is None:
        cliente = await cliente_repository.criar(
            Cliente(
                id=uuid4(),
                nome=dados.pushName or telefone,
                telefone=telefone,
                criado_em=datetime.now(timezone.utc),
            )
        )

    mensagem_use_cases = MensagemUseCases(SqlAlchemyMensagemRepository(session), classificador)
    await mensagem_use_cases.receber(cliente.id, texto)

    return WhatsappWebhookOut(status="processado", tipo=dados.messageType)
