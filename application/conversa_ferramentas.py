from typing import Any

_CONSULTAR_PRECO_PECA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "consultar_preco_peca",
        "description": "Consulta preço e estoque de uma peça pelo nome ou descrição.",
        "parameters": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "Nome ou descrição da peça buscada"},
            },
            "required": ["nome"],
        },
    },
}

_CONSULTAR_STATUS_PROTOCOLO: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "consultar_status_protocolo",
        "description": (
            "Consulta o status de um protocolo (ordem de serviço) do "
            "cliente pelo número — aguardando aprovação, em execução, "
            "pronto ou cancelado."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "numero": {
                    "type": "integer",
                    "description": "Número do protocolo que o cliente quer consultar",
                },
            },
            "required": ["numero"],
        },
    },
}

_CRIAR_PEDIDO: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "criar_pedido",
        "description": (
            "Cria pedido de venda direta. Só chamar após o cliente "
            "confirmar a compra — nunca só por perguntar o preço."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "peca_id": {
                    "type": "string",
                    "description": "ID interno da peça, obtido via consultar_preco_peca — nunca mostre esse valor ao cliente",
                },
                "quantidade": {"type": "integer", "description": "Quantidade de unidades"},
                "tipo_entrega": {
                    "type": "string",
                    "enum": ["retirada_local", "envio_remoto"],
                },
                "endereco_entrega": {
                    # ["string", "null"], não só "string": o modelo costuma
                    # mandar null explícito (em vez de omitir a chave) quando
                    # o campo não se aplica (retirada_local) — schema "string"
                    # puro faz a Groq rejeitar a chamada inteira com 400
                    # (validação estrita), derrubando o pedido sem aviso
                    # nenhum pro cliente. Bug real visto em produção.
                    "type": ["string", "null"],
                    "description": "Endereço completo — obrigatório só se tipo_entrega for envio_remoto",
                },
            },
            "required": ["peca_id", "quantidade", "tipo_entrega"],
        },
    },
}

_CANCELAR_PEDIDO: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "cancelar_pedido",
        "description": (
            "Cancela um pedido do cliente pelo número. Só chamar depois que "
            "o cliente confirmar que quer cancelar de verdade — nunca só "
            "por ele reclamar ou hesitar."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "numero": {
                    "type": "integer",
                    "description": "Número do pedido que o cliente quer cancelar",
                },
            },
            "required": ["numero"],
        },
    },
}

_AGENDAR_VISITA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "agendar_visita",
        "description": (
            "Agenda visita presencial pra avaliar dano estrutural (batida, "
            "amassado, pintura, lanternagem) ou outro serviço mecânico. Só "
            "chamar após o cliente confirmar data e horário — nunca só "
            "porque ele mencionou uma peça (isso é consultar_preco_peca, "
            "não agendamento)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "data_hora": {
                    "type": "string",
                    "description": "Data e hora da visita em ISO 8601 (ex: 2026-08-10T14:00:00)",
                },
                "descricao": {
                    "type": "string",
                    "description": (
                        "Resumo curto do problema relatado e do veículo (ex: "
                        "'moto Honda Fan 160, caiu, guidão entortado') — é o que "
                        "o mecânico vai ler antes da visita, sem precisar reler "
                        "a conversa inteira."
                    ),
                },
                "especialidades": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "funilaria_pintura",
                            "eletrica",
                            "mecanica_geral",
                            "montagem",
                            "indefinido",
                        ],
                    },
                    "description": (
                        "Área(s) responsável(is) pelo serviço, pelo relato do "
                        "cliente — nunca pergunte isso diretamente ao cliente, "
                        "infira do que ele já contou. funilaria_pintura = dano "
                        "visível (batida, amassado, pintura, lanternagem); "
                        "eletrica = luz/sistema elétrico; mecanica_geral = "
                        "motor/câmbio/suspensão/freios; montagem = pedido "
                        "explícito de instalação de peça. Pode ter mais de "
                        "uma (ex: batida com problema elétrico junto). Se "
                        "genuinamente não der pra inferir, use só "
                        "['indefinido']."
                    ),
                },
                "confianca": {
                    "type": "string",
                    "enum": ["alta", "media", "baixa"],
                    "description": (
                        "Sua confiança na(s) especialidade(s) acima, pelo que o "
                        "cliente relatou. alta = o relato deixa claro qual "
                        "área (ex: 'bati o carro' = funilaria_pintura óbvio). "
                        "media = tem indício mas não é 100% certo. baixa = "
                        "você está chutando entre opções ou o relato é vago "
                        "demais pra ter certeza — nesse caso pode sugerir uma "
                        "especialidade específica mesmo assim, o sistema "
                        "ajusta sozinho quando a confiança é baixa."
                    ),
                },
            },
            "required": ["data_hora", "descricao", "especialidades", "confianca"],
        },
    },
}

_TRANSFERIR_ATENDIMENTO: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "transferir_atendimento",
        "description": (
            "Transfere a conversa pra um atendente humano. Use quando não "
            "conseguir ajudar o cliente, ele insistir em algo fora do que "
            "você resolve, ou a situação precisar claramente de uma pessoa."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "motivo": {
                    "type": "string",
                    "description": "Resumo curto do motivo — ajuda o atendente a entender o contexto rápido",
                },
            },
            "required": ["motivo"],
        },
    },
}

# Regra 1 do CLAUDE.md: dano estrutural nunca pode virar venda de peça nem
# orçamento pela IA — por isso essa categoria (e agendamento geral, mesma
# necessidade: só marcar visita) tem sua PRÓPRIA lista de ferramentas (só
# agendar_visita), nunca consultar_preco_peca/criar_pedido. Sem isso, um
# pedido de agendamento comum caía no fluxo de venda, sem ferramenta
# nenhuma pra criar o agendamento de verdade — a IA "confirmava" data e
# horário de boca, sem nada salvo no banco.
# transferir_atendimento entra em todas as listas — a IA pode precisar pedir
# ajuda humana em qualquer tipo de conversa, não só numa categoria.
FERRAMENTAS_VENDA = [
    _CONSULTAR_PRECO_PECA,
    _CRIAR_PEDIDO,
    _CANCELAR_PEDIDO,
    _CONSULTAR_STATUS_PROTOCOLO,
    _TRANSFERIR_ATENDIMENTO,
]
FERRAMENTAS_AGENDAMENTO = [_AGENDAR_VISITA, _TRANSFERIR_ATENDIMENTO]
# Regra 4 do CLAUDE.md: nunca tentar vender pra quem parece estar
# reclamando — só transferir_atendimento disponível, nada de venda.
FERRAMENTAS_RECLAMACAO_SENSIVEL = [_TRANSFERIR_ATENDIMENTO]


def endereco_parece_valido(endereco: str | None) -> bool:
    # O prompt já pede pra IA perguntar o endereço antes de chamar
    # criar_pedido, mas isso não é 100% confiável (já vimos o modelo
    # inventar uma frase tipo "por favor, forneça o endereço" e mandar isso
    # como se fosse o endereço real). Regra 3 do CLAUDE.md: nunca confiar só
    # na conversa — endereço real de entrega quase sempre tem número, então
    # isso funciona como checagem determinística.
    if endereco is None:
        return False
    texto = endereco.strip()
    return len(texto) >= 10 and any(c.isdigit() for c in texto)


    
