from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.admin import registrar_admin
from infrastructure.routers import (
    agendamentos,
    auth,
    clientes,
    configuracao_oficina,
    itens_adicionais,
    mensagens,
    movimentacoes_estoque,
    pecas,
    pedidos,
    protocolos,
    relatorios,
    veiculos,
    webhook,
)

app = FastAPI(title="Wrench IQ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3011", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(pecas.router)
app.include_router(mensagens.router)
app.include_router(auth.router)
app.include_router(protocolos.router)
app.include_router(clientes.router)
app.include_router(pedidos.router)
app.include_router(veiculos.router)
app.include_router(agendamentos.router)
app.include_router(movimentacoes_estoque.router)
app.include_router(configuracao_oficina.router)
app.include_router(itens_adicionais.router)
app.include_router(relatorios.router)

registrar_admin(app)
