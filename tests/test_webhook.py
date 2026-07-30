import copy
import json
import uuid
from pathlib import Path

from adapters.orm_models import ClienteORM, MensagemORM
from tests.conftest import TestSessionLocal

_EXEMPLOS = json.loads((Path(__file__).parent / "exemplos_payload.json").read_text())


def _payload_com_telefone_unico(nome_exemplo: str) -> dict:
    payload = copy.deepcopy(_EXEMPLOS[nome_exemplo])
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"
    payload["data"]["key"]["remoteJid"] = f"{telefone}@s.whatsapp.net"
    return payload


async def test_webhook_retorna_mensagem_recebida(client):
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"

    resposta = await client.post(
        "/webhook", json={"telefone": telefone, "mensagem": "teste"}
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"resposta": "recebi sua mensagem: teste"}


async def test_webhook_cria_cliente_novo_e_persiste_mensagem(client):
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"

    resposta = await client.post(
        "/webhook", json={"telefone": telefone, "mensagem": "Qual o preço do farol?"}
    )
    assert resposta.status_code == 200

    async with TestSessionLocal() as session:
        result = await session.execute(
            ClienteORM.__table__.select().where(ClienteORM.telefone == telefone)
        )
        cliente = result.first()
        assert cliente is not None

        result = await session.execute(
            MensagemORM.__table__.select().where(MensagemORM.cliente_id == cliente.id)
        )
        mensagem = result.first()

    assert mensagem is not None
    assert mensagem.categoria == "consulta_peca"


async def test_webhook_reaproveita_cliente_existente(client):
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"

    await client.post("/webhook", json={"telefone": telefone, "mensagem": "oi"})
    await client.post("/webhook", json={"telefone": telefone, "mensagem": "de novo"})

    async with TestSessionLocal() as session:
        result = await session.execute(
            ClienteORM.__table__.select().where(ClienteORM.telefone == telefone)
        )
        clientes = result.all()

    assert len(clientes) == 1


async def test_webhook_whatsapp_processa_texto_e_usa_pushname(client):
    payload = _payload_com_telefone_unico("texto")
    telefone = payload["data"]["key"]["remoteJid"].split("@")[0]

    resposta = await client.post("/webhook/whatsapp", json=payload)

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "processado", "tipo": "conversation"}

    async with TestSessionLocal() as session:
        result = await session.execute(
            ClienteORM.__table__.select().where(ClienteORM.telefone == telefone)
        )
        cliente = result.first()
        assert cliente is not None
        assert cliente.nome == payload["data"]["pushName"]

        result = await session.execute(
            MensagemORM.__table__.select().where(MensagemORM.cliente_id == cliente.id)
        )
        mensagem = result.first()

    assert mensagem is not None
    assert mensagem.categoria == "consulta_peca"


async def test_webhook_whatsapp_audio_e_imagem_reconhecidos_sem_processar(client):
    for nome_exemplo, tipo_esperado in [("audio", "audioMessage"), ("imagem", "imageMessage")]:
        payload = _payload_com_telefone_unico(nome_exemplo)
        telefone = payload["data"]["key"]["remoteJid"].split("@")[0]

        resposta = await client.post("/webhook/whatsapp", json=payload)

        assert resposta.status_code == 200
        assert resposta.json() == {
            "status": "recebido_sem_processamento",
            "tipo": tipo_esperado,
        }

        async with TestSessionLocal() as session:
            result = await session.execute(
                ClienteORM.__table__.select().where(ClienteORM.telefone == telefone)
            )
            assert result.first() is None


async def test_webhook_whatsapp_ignora_eco_da_propria_instancia(client):
    payload = _payload_com_telefone_unico("eco_da_propria_instancia")
    telefone = payload["data"]["key"]["remoteJid"].split("@")[0]

    resposta = await client.post("/webhook/whatsapp", json=payload)

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ignorado", "tipo": "conversation"}

    async with TestSessionLocal() as session:
        result = await session.execute(
            ClienteORM.__table__.select().where(ClienteORM.telefone == telefone)
        )
        assert result.first() is None
