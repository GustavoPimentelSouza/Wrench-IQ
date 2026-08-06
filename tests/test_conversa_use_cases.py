from datetime import datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

from application.chat_service import ChamadaFerramenta, RespostaChat
from application.conversa_use_cases import ConversaUseCases
from application.pedido_use_cases import EstoqueInsuficienteError, TransicaoInvalidaError
from domain.configuracao_oficina import ConfiguracaoOficina
from domain.mensagem import CategoriaMensagem, Mensagem, MotivoAtendimento
from domain.peca import Peca
from domain.pedido import Pedido, StatusPedido, TipoEntrega
from domain.protocolo import Protocolo, StatusProtocolo
from tests.fakes import (
    FakeAgendamentoUseCases,
    FakeChatService,
    FakeChatServiceComErro,
    FakeConfiguracaoOficinaUseCases,
    FakePecaRepository,
    FakePedidoUseCases,
    FakeProtocoloUseCases,
)

# Testes unitários de ConversaUseCases — sem HTTP, sem banco, tudo com
# fakes. O que importa aqui é a lógica de orquestração (qual ferramenta fica
# disponível, quando bloqueia, quando finaliza sem chamar a IA de novo), não
# o comportamento real do Groq (isso não dá pra testar de forma
# determinística — ver tests/test_groq_integracao_real.py).

_CONFIG_PADRAO = ConfiguracaoOficina(
    id=1,
    nome_empresa="Oficina Teste",
    horario_semana_abertura=time(8, 0),
    horario_semana_fechamento=time(19, 0),
    horario_sabado_abertura=time(8, 0),
    horario_sabado_fechamento=time(18, 0),
    horario_domingo_abertura=None,
    horario_domingo_fechamento=None,
)

_PECA = Peca(
    id=uuid4(),
    nome="Paralama",
    marca_modelo_compativel="Honda Fan 160",
    ano_compativel="2020-2024",
    preco=Decimal("120.00"),
    quantidade_estoque=5,
    criado_em=datetime.now(timezone.utc),
)

_PECA_ROSA = Peca(
    id=uuid4(),
    nome="Paralama",
    marca_modelo_compativel="Honda Fan 160",
    ano_compativel="2020-2024",
    preco=Decimal("135.00"),
    quantidade_estoque=3,
    cor="rosa",
    criado_em=datetime.now(timezone.utc),
)


def _montar_conversa(
    chat_service=None,
    pedido_use_cases=None,
    agendamento_use_cases=None,
    protocolo_use_cases=None,
    pecas=None,
) -> ConversaUseCases:
    return ConversaUseCases(
        chat_service=chat_service or FakeChatService(),
        peca_repository=FakePecaRepository(pecas or [_PECA]),
        pedido_use_cases=pedido_use_cases or FakePedidoUseCases(),
        configuracao_oficina_use_cases=FakeConfiguracaoOficinaUseCases(_CONFIG_PADRAO),
        agendamento_use_cases=agendamento_use_cases or FakeAgendamentoUseCases(),
        protocolo_use_cases=protocolo_use_cases or FakeProtocoloUseCases(),
    )


def _nomes_ferramentas(ferramentas: list[dict]) -> set[str]:
    return {f["function"]["name"] for f in ferramentas}


async def test_saudacao_nao_chama_ia():
    chat = FakeChatService()
    conversa = _montar_conversa(chat_service=chat)

    resultado = await conversa.responder("oi", uuid4(), CategoriaMensagem.NAO_IDENTIFICADO)

    assert "peça" in resultado.texto.lower()
    assert chat.ferramentas_recebidas == []  # IA nunca foi chamada


async def test_consultar_preco_peca_prefere_variante_com_a_cor_pedida():
    # buscar_por_nome_aproximado ordena pela proximidade semântica GERAL do
    # texto, não por cor — a peça rosa pode vir em 2º lugar, não em [0]. Sem
    # a seleção por cor, cadastrar a variante rosa no catálogo não
    # adiantaria nada: a IA nunca chegaria a vê-la, e diria "não temos essa
    # cor" com a peça certa bem ali na lista de candidatas.
    chamada = ChamadaFerramenta(
        id="call_1", nome="consultar_preco_peca", argumentos={"nome": "paralama fan 160 rosa"}
    )
    # Só uma resposta na fila: depois do resultado da ferramenta, o
    # FakeChatService cai no fallback (ecoa a última mensagem, que é o
    # próprio resultado da ferramenta) — dá pra conferir direto no texto
    # final sem precisar simular uma segunda resposta da IA.
    chat = FakeChatService(respostas=[RespostaChat(texto=None, chamadas_ferramentas=[chamada])])
    # Ordem proposital: a peça sem cor primeiro, a rosa depois — simula o
    # caso em que a busca semântica não rankeia a variante certa em 1º.
    conversa = _montar_conversa(chat_service=chat, pecas=[_PECA, _PECA_ROSA])

    resultado = await conversa.responder(
        "quero um paralama fan 160 rosa", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert "135" in resultado.texto
    assert "120" not in resultado.texto


async def test_reclamacao_sensivel_so_oferece_transferir_e_nunca_venda():
    # Regra 4 do CLAUDE.md: reclamação sensível nunca pode virar venda de
    # peça — só transferir_atendimento fica disponível pra IA nesse modo.
    chamada = ChamadaFerramenta(id="call_1", nome="transferir_atendimento", argumentos={"motivo": "Cliente insatisfeito"})
    chat = FakeChatService(respostas=[RespostaChat(texto=None, chamadas_ferramentas=[chamada])])
    conversa = _montar_conversa(chat_service=chat)

    resultado = await conversa.responder(
        "isso é um absurdo, quero reclamar", uuid4(), CategoriaMensagem.RECLAMACAO_SENSIVEL
    )

    assert resultado.precisa_atendimento_humano is True
    assert resultado.motivo_atendimento == MotivoAtendimento.TRANSFERENCIA_IA
    ferramentas_oferecidas = _nomes_ferramentas(chat.ferramentas_recebidas[0])
    assert ferramentas_oferecidas == {"transferir_atendimento"}


async def test_reclamacao_sensivel_mal_classificada_nao_trava_confirmacao():
    # A categoria vem de classificar só a mensagem atual, sem ver o
    # histórico — pode errar em mensagens curtas e ambíguas (ex: "sim"
    # confirmando uma peça, sem nenhum sinal de reclamação nela mesma). A
    # IA recebe o histórico completo e decide de verdade; uma classificação
    # errada não pode travar a conversa sem chance de recuperação.
    chat = FakeChatService()
    historico = [
        Mensagem(
            id=uuid4(),
            cliente_id=uuid4(),
            texto="quero o farol da cg 160",
            categoria=CategoriaMensagem.CONSULTA_PECA,
            criado_em=datetime.now(timezone.utc),
            resposta_ia="Achei o Farol dianteiro (Honda CG 160). É essa a peça?",
        )
    ]
    conversa = _montar_conversa(chat_service=chat)

    resultado = await conversa.responder(
        "sim", uuid4(), CategoriaMensagem.RECLAMACAO_SENSIVEL, historico=historico
    )

    assert resultado.precisa_atendimento_humano is False
    ferramentas_oferecidas = _nomes_ferramentas(chat.ferramentas_recebidas[0])
    assert ferramentas_oferecidas == {"transferir_atendimento"}


async def test_dano_estrutural_so_oferece_agendar_visita():
    # Regra 1 do CLAUDE.md: dano estrutural nunca pode virar venda de peça.
    chat = FakeChatService()
    conversa = _montar_conversa(chat_service=chat)

    await conversa.responder(
        "bati o carro e amassou a lateral", uuid4(), CategoriaMensagem.DANO_ESTRUTURAL
    )

    ferramentas_oferecidas = _nomes_ferramentas(chat.ferramentas_recebidas[0])
    assert ferramentas_oferecidas == {"agendar_visita", "transferir_atendimento"}


async def test_agendar_visita_salva_descricao_pro_mecanico_ler_depois():
    # Dor real do dia a dia: sem isso, o mecânico só via nome+horário na
    # Agenda, sem saber o motivo da visita nem o veículo — tinha que
    # reperguntar tudo que a IA já apurou no chat.
    chamada = ChamadaFerramenta(
        id="call_1",
        nome="agendar_visita",
        argumentos={
            "data_hora": "2026-08-10T14:00:00",
            "descricao": "Honda Fan 160, caiu da moto, guidão entortado",
        },
    )
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Visita agendada pra 10/08 às 14h."),
        ]
    )
    agendamentos = FakeAgendamentoUseCases()
    conversa = _montar_conversa(chat_service=chat, agendamento_use_cases=agendamentos)

    await conversa.responder(
        "bati com a moto e o guidão entortou", uuid4(), CategoriaMensagem.DANO_ESTRUTURAL
    )

    assert agendamentos.ultimo_agendamento.descricao == "Honda Fan 160, caiu da moto, guidão entortado"


async def test_dano_estrutural_gruda_mesmo_se_mensagem_atual_for_reclassificada():
    # Bug real encontrado em teste manual: a classificação é por mensagem
    # (sem memória), então "pode ser dia 10 às 14h" sozinha vem como
    # categoria "agendamento" — mas a conversa inteira ainda é sobre dano
    # estrutural, e não pode virar venda de peça no meio do caminho.
    chat = FakeChatService()
    conversa = _montar_conversa(chat_service=chat)
    historico = [
        Mensagem(
            id=uuid4(),
            cliente_id=uuid4(),
            texto="bati o carro",
            categoria=CategoriaMensagem.DANO_ESTRUTURAL,
            criado_em=datetime.now(timezone.utc),
            resposta_ia="Sinto muito! Que data prefere pra visita?",
        )
    ]

    await conversa.responder(
        "pode ser dia 10 às 14h",
        uuid4(),
        CategoriaMensagem.AGENDAMENTO,
        historico=historico,
    )

    ferramentas_oferecidas = _nomes_ferramentas(chat.ferramentas_recebidas[0])
    assert ferramentas_oferecidas == {"agendar_visita", "transferir_atendimento"}


async def test_criar_pedido_envio_remoto_com_endereco_invalido_nao_cria_pedido():
    # Regra 3 do CLAUDE.md: nunca confiar cegamente na conversa/IA — já
    # vimos o modelo inventar um texto tipo "por favor, forneça o endereço"
    # em vez do endereço real.
    chamada = ChamadaFerramenta(
        id="call_1",
        nome="criar_pedido",
        argumentos={
            "peca_id": str(_PECA.id),
            "quantidade": 1,
            "tipo_entrega": "envio_remoto",
            "endereco_entrega": "Por favor, forneça o endereço de entrega.",
        },
    )
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Só preciso do seu endereço completo pra continuar."),
        ]
    )
    pedidos = FakePedidoUseCases()
    conversa = _montar_conversa(chat_service=chat, pedido_use_cases=pedidos)

    resultado = await conversa.responder(
        "quero comprar, envia pra minha casa", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert pedidos.ultima_chamada is None  # pedido nunca foi criado
    assert "endereço" in resultado.texto.lower()


async def test_criar_pedido_com_sucesso_finaliza_sem_segunda_chamada_a_ia():
    # Já vimos a IA "esquecer" de repassar número de pedido/preço ao
    # parafrasear — por isso a confirmação de sucesso é devolvida direto,
    # sem dar mais uma chance da IA reescrever (só 1 chamada à IA no total).
    pedido = Pedido(
        id=uuid4(),
        cliente_id=uuid4(),
        peca_id=_PECA.id,
        quantidade=1,
        valor_total=Decimal("120.00"),
        tipo_entrega=TipoEntrega.RETIRADA_LOCAL,
        status=StatusPedido.AGUARDANDO_RETIRADA,
        criado_em=datetime.now(timezone.utc),
        numero=999,
    )
    chamada = ChamadaFerramenta(
        id="call_1",
        nome="criar_pedido",
        argumentos={
            "peca_id": str(_PECA.id),
            "quantidade": 1,
            "tipo_entrega": "retirada_local",
        },
    )
    chat = FakeChatService(respostas=[RespostaChat(texto=None, chamadas_ferramentas=[chamada])])
    pedidos = FakePedidoUseCases(pedido=pedido)
    conversa = _montar_conversa(chat_service=chat, pedido_use_cases=pedidos)

    resultado = await conversa.responder(
        "confirmo, quero retirar na loja", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert "#999" in resultado.texto
    assert "120.00" in resultado.texto
    assert len(chat.ferramentas_recebidas) == 1  # só 1 rodada, não pediu resumo final


async def test_estoque_insuficiente_nao_finaliza_pedido():
    chamada = ChamadaFerramenta(
        id="call_1",
        nome="criar_pedido",
        argumentos={
            "peca_id": str(_PECA.id),
            "quantidade": 10,
            "tipo_entrega": "retirada_local",
        },
    )
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Não temos estoque suficiente no momento."),
        ]
    )
    pedidos = FakePedidoUseCases(erro=EstoqueInsuficienteError())
    conversa = _montar_conversa(chat_service=chat, pedido_use_cases=pedidos)

    resultado = await conversa.responder(
        "quero 10 unidades, retirada na loja", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert "estoque" in resultado.texto.lower()


async def test_falha_tecnica_cai_no_fallback_e_marca_atendimento_humano():
    # Regra 4 do CLAUDE.md: falha técnica cai pro atendente humano.
    conversa = _montar_conversa(chat_service=FakeChatServiceComErro())

    resultado = await conversa.responder(
        "quanto custa o farol?", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert resultado.precisa_atendimento_humano is True
    assert resultado.motivo_atendimento == MotivoAtendimento.FALHA_TECNICA


async def test_preco_sugerido_pelo_cliente_sem_ferramenta_e_bloqueado():
    # Regra 3 do CLAUDE.md: preço nunca vem da conversa. Bug real: cliente
    # sugeriu um preço ("não custa 45 reais?") e a IA confirmou sem chamar
    # consultar_preco_peca nenhuma vez — nenhuma garantia de que é real.
    chat = FakeChatService(
        respostas=[RespostaChat(texto="Sim, o farol está disponível por R$ 45,00.")]
    )
    conversa = _montar_conversa(chat_service=chat)

    resultado = await conversa.responder(
        "o farol não custa 45 reais? me cobra esse valor",
        uuid4(),
        CategoriaMensagem.CONSULTA_PECA,
    )

    assert "45" not in resultado.texto
    assert resultado.ferramentas_chamadas == []


async def test_transferir_atendimento_finaliza_com_motivo_transferencia_ia():
    # Terceira opção da fila de atendimento: a própria IA decide que precisa
    # de humano (diferente de reclamação sensível, que é decidido antes de
    # chamar a IA, pela classificação).
    chamada = ChamadaFerramenta(
        id="call_1",
        nome="transferir_atendimento",
        argumentos={"motivo": "Cliente pedindo algo fora do que consigo resolver"},
    )
    chat = FakeChatService(respostas=[RespostaChat(texto=None, chamadas_ferramentas=[chamada])])
    conversa = _montar_conversa(chat_service=chat)

    resultado = await conversa.responder(
        "preciso de uma coisa bem específica", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert resultado.precisa_atendimento_humano is True
    assert resultado.motivo_atendimento == MotivoAtendimento.TRANSFERENCIA_IA
    assert "atendente humano" in resultado.texto.lower()
    assert len(chat.ferramentas_recebidas) == 1  # finalizou sem pedir resumo final


async def test_cancelar_pedido_com_sucesso_finaliza():
    pedido_existente = Pedido(
        id=uuid4(),
        cliente_id=uuid4(),
        peca_id=_PECA.id,
        quantidade=1,
        valor_total=Decimal("120.00"),
        tipo_entrega=TipoEntrega.RETIRADA_LOCAL,
        status=StatusPedido.AGUARDANDO_RETIRADA,
        criado_em=datetime.now(timezone.utc),
        numero=250,
    )
    chamada = ChamadaFerramenta(id="call_1", nome="cancelar_pedido", argumentos={"numero": 250})
    chat = FakeChatService(respostas=[RespostaChat(texto=None, chamadas_ferramentas=[chamada])])
    pedidos = FakePedidoUseCases(pedidos_do_cliente=[pedido_existente])
    conversa = _montar_conversa(chat_service=chat, pedido_use_cases=pedidos)

    resultado = await conversa.responder(
        "quero cancelar o pedido 250", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert "#250" in resultado.texto
    assert "cancelado" in resultado.texto.lower()
    assert pedidos.cancelado_id == pedido_existente.id


async def test_cancelar_pedido_de_outro_cliente_nao_encontra():
    # Busca só entre os pedidos do cliente que está conversando — nunca por
    # ID direto, senão daria pra cancelar pedido de outra pessoa só
    # chutando um número.
    chamada = ChamadaFerramenta(id="call_1", nome="cancelar_pedido", argumentos={"numero": 999})
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Não encontrei esse pedido pra você."),
        ]
    )
    pedidos = FakePedidoUseCases(pedidos_do_cliente=[])
    conversa = _montar_conversa(chat_service=chat, pedido_use_cases=pedidos)

    await conversa.responder("cancela o pedido 999", uuid4(), CategoriaMensagem.CONSULTA_PECA)

    assert pedidos.cancelado_id is None


async def test_cancelar_pedido_ja_entregue_nao_permite():
    pedido_existente = Pedido(
        id=uuid4(),
        cliente_id=uuid4(),
        peca_id=_PECA.id,
        quantidade=1,
        valor_total=Decimal("120.00"),
        tipo_entrega=TipoEntrega.RETIRADA_LOCAL,
        status=StatusPedido.ENTREGUE,
        criado_em=datetime.now(timezone.utc),
        numero=251,
    )
    chamada = ChamadaFerramenta(id="call_1", nome="cancelar_pedido", argumentos={"numero": 251})
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Esse pedido já foi entregue, não dá pra cancelar."),
        ]
    )
    pedidos = FakePedidoUseCases(
        pedidos_do_cliente=[pedido_existente], erro_cancelar=TransicaoInvalidaError()
    )
    conversa = _montar_conversa(chat_service=chat, pedido_use_cases=pedidos)

    await conversa.responder("cancela o pedido 251", uuid4(), CategoriaMensagem.CONSULTA_PECA)

    assert pedidos.cancelado_id is None


async def test_consultar_status_protocolo_com_sucesso():
    protocolo_existente = Protocolo(
        id=uuid4(),
        cliente_id=uuid4(),
        veiculo="Honda Fan 160",
        categoria="dano_estrutural",
        status=StatusProtocolo.EM_EXECUCAO,
        criado_em=datetime.now(timezone.utc),
        numero=42,
    )
    chamada = ChamadaFerramenta(
        id="call_1", nome="consultar_status_protocolo", argumentos={"numero": 42}
    )
    # consultar_status_protocolo não finaliza sozinho (diferente de
    # cancelar_pedido) — o resultado da ferramenta volta pra IA repassar ao
    # cliente, por isso a fila tem uma segunda resposta simulando isso.
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Protocolo #42 está em execução."),
        ]
    )
    protocolos = FakeProtocoloUseCases(protocolos_do_cliente=[protocolo_existente])
    conversa = _montar_conversa(chat_service=chat, protocolo_use_cases=protocolos)

    resultado = await conversa.responder(
        "qual o status do protocolo 42", uuid4(), CategoriaMensagem.STATUS_PROTOCOLO
    )

    assert "#42" in resultado.texto
    assert "em execução" in resultado.texto.lower()


async def test_consultar_status_protocolo_de_outro_cliente_nao_encontra():
    # Mesma proteção de cancelar_pedido: busca só entre os protocolos do
    # cliente que está conversando, nunca por ID/número direto — senão daria
    # pra ver o status do protocolo de outra pessoa só chutando o número.
    chamada = ChamadaFerramenta(
        id="call_1", nome="consultar_status_protocolo", argumentos={"numero": 999}
    )
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Não encontrei esse protocolo pra você."),
        ]
    )
    protocolos = FakeProtocoloUseCases(protocolos_do_cliente=[])
    conversa = _montar_conversa(chat_service=chat, protocolo_use_cases=protocolos)

    resultado = await conversa.responder(
        "status do protocolo 999", uuid4(), CategoriaMensagem.STATUS_PROTOCOLO
    )

    assert "não encontrei" in resultado.texto.lower()
