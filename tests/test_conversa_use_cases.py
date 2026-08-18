from dataclasses import replace
from datetime import datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

from application.chat_service import ChamadaFerramenta, RespostaChat
from application.conversa_prompts import MENSAGEM_LIMITE_TROCAS
from application.conversa_use_cases import ConversaUseCases
from application.pedido_use_cases import EstoqueInsuficienteError, TransicaoInvalidaError
from domain.configuracao_oficina import ConfiguracaoOficina
from domain.especialidade import Especialidade
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
    sugestoes=None,
) -> ConversaUseCases:
    return ConversaUseCases(
        chat_service=chat_service or FakeChatService(),
        peca_repository=FakePecaRepository(
            pecas if pecas is not None else [_PECA], sugestoes=sugestoes
        ),
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


async def test_confirmar_encerramento_apos_pedido_nao_chama_ia_nem_cria_pedido_de_novo():
    # Bug real encontrado em teste manual: cliente confirma "só isso mesmo"
    # logo depois de um pedido criado, e o modelo chamava criar_pedido de
    # novo pra mesma compra em vez de encerrar. Isso não pode depender do
    # modelo acertar — precisa ser decidido antes de chamar a IA.
    chat = FakeChatService()
    historico = [
        Mensagem(
            id=uuid4(),
            cliente_id=uuid4(),
            texto="uma e vou aí retirar na loja",
            categoria=CategoriaMensagem.CONSULTA_PECA,
            criado_em=datetime.now(timezone.utc),
            resposta_ia="Pedido #302 confirmado! Vela de ignição — R$ 22.50.",
            acao_finalizadora="criar_pedido",
        )
    ]
    conversa = _montar_conversa(chat_service=chat)

    resultado = await conversa.responder(
        "só isso mesmo", uuid4(), CategoriaMensagem.CONSULTA_PECA, historico=historico
    )

    assert chat.ferramentas_recebidas == []  # IA nem chegou a ser chamada
    assert resultado.ferramentas_chamadas == []
    assert resultado.texto == "Por nada! Qualquer coisa, é só chamar."


async def test_confirmar_encerramento_usa_mensagem_configurada_da_oficina():
    chat = FakeChatService()
    configuracao = ConfiguracaoOficina(
        id=1,
        nome_empresa="Oficina Teste",
        horario_semana_abertura=time(8, 0),
        horario_semana_fechamento=time(19, 0),
        horario_sabado_abertura=time(8, 0),
        horario_sabado_fechamento=time(18, 0),
        horario_domingo_abertura=None,
        horario_domingo_fechamento=None,
        mensagem_encerramento="Agradecemos seu contato com a Oficina Dugrau!",
    )
    conversa = ConversaUseCases(
        chat_service=chat,
        peca_repository=FakePecaRepository([_PECA]),
        pedido_use_cases=FakePedidoUseCases(),
        configuracao_oficina_use_cases=FakeConfiguracaoOficinaUseCases(configuracao),
        agendamento_use_cases=FakeAgendamentoUseCases(),
        protocolo_use_cases=FakeProtocoloUseCases(),
    )
    historico = [
        Mensagem(
            id=uuid4(),
            cliente_id=uuid4(),
            texto="pode agendar pra dia 10",
            categoria=CategoriaMensagem.AGENDAMENTO,
            criado_em=datetime.now(timezone.utc),
            resposta_ia="Visita agendada pra 10/08 às 14h.",
            acao_finalizadora="agendar_visita",
        )
    ]

    resultado = await conversa.responder(
        "valeu", uuid4(), CategoriaMensagem.AGENDAMENTO, historico=historico
    )

    assert resultado.texto == "Agradecemos seu contato com a Oficina Dugrau!"


async def test_confirmacao_encerramento_sem_acao_anterior_segue_fluxo_normal():
    # "só isso" sozinho, sem um pedido/agendamento recém-concluído antes,
    # não deve travar a conversa — só dispara a checagem determinística
    # nesse cenário específico, não em qualquer "só isso" da vida.
    chat = FakeChatService()
    historico = [
        Mensagem(
            id=uuid4(),
            cliente_id=uuid4(),
            texto="vocês têm pastilha de freio?",
            categoria=CategoriaMensagem.CONSULTA_PECA,
            criado_em=datetime.now(timezone.utc),
            resposta_ia="Ainda não achei — pode confirmar o modelo?",
            acao_finalizadora=None,
        )
    ]
    conversa = _montar_conversa(chat_service=chat)

    await conversa.responder(
        "só isso mesmo", uuid4(), CategoriaMensagem.CONSULTA_PECA, historico=historico
    )

    assert len(chat.ferramentas_recebidas) == 1  # IA foi chamada normalmente


async def test_consultar_peca_sem_match_confiante_sugere_parecidas():
    # Bug real encontrado em teste manual: "vela da fan 106" (erro de
    # digitação de "fan 160") não batia o limite de confiança e virava
    # "não encontrei nada", mesmo a peça certa existindo no catálogo. Agora
    # cai numa lista de sugestão em vez de beco sem saída.
    chamada = ChamadaFerramenta(
        id="call_1", nome="consultar_preco_peca", argumentos={"nome": "vela da fan 106"}
    )
    chat = FakeChatService(respostas=[RespostaChat(texto=None, chamadas_ferramentas=[chamada])])
    conversa = _montar_conversa(chat_service=chat, pecas=[], sugestoes=[_PECA])

    resultado = await conversa.responder(
        "quero uma vela da fan 106", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert _PECA.nome in resultado.texto
    assert str(_PECA.id) in resultado.texto
    assert "não chame consultar_preco_peca de novo" in resultado.texto


async def test_consultar_peca_sem_nenhum_match_mesmo_no_limite_largo_mantem_mensagem_padrao():
    chamada = ChamadaFerramenta(
        id="call_1", nome="consultar_preco_peca", argumentos={"nome": "pneu de caminhão"}
    )
    chat = FakeChatService(respostas=[RespostaChat(texto=None, chamadas_ferramentas=[chamada])])
    conversa = _montar_conversa(chat_service=chat, pecas=[], sugestoes=[])

    resultado = await conversa.responder(
        "quero um pneu de caminhão", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert "Nenhuma peça parecida encontrada" in resultado.texto


async def test_nao_reenvia_imagem_ja_mostrada_na_conversa():
    # Bug real encontrado em teste manual: a IA rechamou consultar_preco_peca
    # pra confirmar a mesma peça em turnos seguidos, e a mesma foto era
    # reenviada em cada mensagem — poluía o chat sem trazer informação nova.
    peca_com_imagem = replace(_PECA, imagem_url="https://exemplo.com/paralama.jpg")
    chamada = ChamadaFerramenta(
        id="call_1", nome="consultar_preco_peca", argumentos={"nome": "paralama fan 160"}
    )
    chat = FakeChatService(respostas=[RespostaChat(texto=None, chamadas_ferramentas=[chamada])])
    conversa = _montar_conversa(chat_service=chat, pecas=[peca_com_imagem])
    historico = [
        Mensagem(
            id=uuid4(),
            cliente_id=uuid4(),
            texto="quero um paralama fan 160",
            categoria=CategoriaMensagem.CONSULTA_PECA,
            criado_em=datetime.now(timezone.utc),
            resposta_ia="Achamos o Paralama (Honda Fan 160). É essa a peça?",
            imagem_url="https://exemplo.com/paralama.jpg",
        )
    ]

    resultado = await conversa.responder(
        "sim, é essa mesma", uuid4(), CategoriaMensagem.CONSULTA_PECA, historico=historico
    )

    assert resultado.imagem_url is None


async def test_envia_imagem_normalmente_quando_ainda_nao_apareceu_na_conversa():
    peca_com_imagem = replace(_PECA, imagem_url="https://exemplo.com/paralama.jpg")
    chamada = ChamadaFerramenta(
        id="call_1", nome="consultar_preco_peca", argumentos={"nome": "paralama fan 160"}
    )
    chat = FakeChatService(respostas=[RespostaChat(texto=None, chamadas_ferramentas=[chamada])])
    conversa = _montar_conversa(chat_service=chat, pecas=[peca_com_imagem])

    resultado = await conversa.responder(
        "quero um paralama fan 160", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    assert resultado.imagem_url == "https://exemplo.com/paralama.jpg"


async def test_agendar_visita_com_especialidade_unica():
    chamada = ChamadaFerramenta(
        id="call_1",
        nome="agendar_visita",
        argumentos={
            "data_hora": "2026-08-10T14:00:00",
            "descricao": "Honda Fan 160, caiu da moto, guidão entortado",
            "especialidades": ["funilaria_pintura"],
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

    assert agendamentos.ultimo_agendamento.especialidades == [Especialidade.FUNILARIA_PINTURA]


async def test_agendar_visita_com_multiplas_especialidades():
    # Relato com dois problemas juntos (dano visível + elétrico) — a IA
    # deve incluir as duas especialidades, não só uma.
    chamada = ChamadaFerramenta(
        id="call_1",
        nome="agendar_visita",
        argumentos={
            "data_hora": "2026-08-10T14:00:00",
            "descricao": "bateu o carro e o pisca-pisca parou de funcionar",
            "especialidades": ["funilaria_pintura", "eletrica"],
        },
    )
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Visita agendada."),
        ]
    )
    agendamentos = FakeAgendamentoUseCases()
    conversa = _montar_conversa(chat_service=chat, agendamento_use_cases=agendamentos)

    await conversa.responder(
        "bati o carro e o pisca-pisca parou de funcionar",
        uuid4(),
        CategoriaMensagem.DANO_ESTRUTURAL,
    )

    assert set(agendamentos.ultimo_agendamento.especialidades) == {
        Especialidade.FUNILARIA_PINTURA,
        Especialidade.ELETRICA,
    }


async def test_agendar_visita_indefinido_persiste_como_indefinido():
    # 'indefinido' é um valor de verdade do enum (ver domain/especialidade.py)
    # — persiste como está. Só a busca de disponibilidade (não a criação)
    # trata isso como mecânica geral; ver test_agendamentos.py.
    chamada = ChamadaFerramenta(
        id="call_1",
        nome="agendar_visita",
        argumentos={
            "data_hora": "2026-08-10T14:00:00",
            "descricao": "cliente não deu detalhes do problema",
            "especialidades": ["indefinido"],
            "confianca": "media",
        },
    )
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Visita agendada."),
        ]
    )
    agendamentos = FakeAgendamentoUseCases()
    conversa = _montar_conversa(chat_service=chat, agendamento_use_cases=agendamentos)

    await conversa.responder(
        "quero marcar uma visita", uuid4(), CategoriaMensagem.AGENDAMENTO
    )

    assert agendamentos.ultimo_agendamento.especialidades == [Especialidade.INDEFINIDO]


async def test_agendar_visita_confianca_baixa_forca_indefinido():
    # Nenhum classificador acerta 100% — quando a própria IA sinaliza baixa
    # confiança, o sistema ignora a especialidade sugerida e força
    # indefinido, sem perguntar nada extra ao cliente.
    chamada = ChamadaFerramenta(
        id="call_1",
        nome="agendar_visita",
        argumentos={
            "data_hora": "2026-08-10T14:00:00",
            "descricao": "carro morre sem motivo aparente às vezes",
            "especialidades": ["mecanica_geral"],
            "confianca": "baixa",
        },
    )
    chat = FakeChatService(
        respostas=[
            RespostaChat(texto=None, chamadas_ferramentas=[chamada]),
            RespostaChat(texto="Visita agendada."),
        ]
    )
    agendamentos = FakeAgendamentoUseCases()
    conversa = _montar_conversa(chat_service=chat, agendamento_use_cases=agendamentos)

    await conversa.responder(
        "meu carro as vezes morre do nada", uuid4(), CategoriaMensagem.AGENDAMENTO
    )

    assert agendamentos.ultimo_agendamento.especialidades == [Especialidade.INDEFINIDO]


async def test_consulta_peca_nunca_oferece_agendar_visita():
    # A distinção entre "quer comprar peça" e "quer agendar visita" não
    # depende da IA decidir certo em texto livre — é estrutural: a
    # categoria consulta_peca simplesmente não tem agendar_visita entre as
    # ferramentas disponíveis, então não tem como a IA chamar essa
    # ferramenta por engano só porque o cliente mencionou uma peça.
    chat = FakeChatService()
    conversa = _montar_conversa(chat_service=chat)

    await conversa.responder(
        "quero comprar um paralama", uuid4(), CategoriaMensagem.CONSULTA_PECA
    )

    ferramentas_oferecidas = _nomes_ferramentas(chat.ferramentas_recebidas[0])
    assert "agendar_visita" not in ferramentas_oferecidas
    assert "consultar_preco_peca" in ferramentas_oferecidas


def _mensagem_consulta_peca(
    resposta_ia: str = "Pode me dar mais detalhes?", ferramentas_chamadas: list[str] | None = None
) -> Mensagem:
    return Mensagem(
        id=uuid4(),
        cliente_id=uuid4(),
        texto="quero uma peça",
        categoria=CategoriaMensagem.CONSULTA_PECA,
        criado_em=datetime.now(timezone.utc),
        resposta_ia=resposta_ia,
        ferramentas_chamadas=ferramentas_chamadas or [],
    )


async def test_primeira_mensagem_sobre_peca_nao_forca_ferramenta():
    # Regra "se vago, pergunte antes" continua livre na 1ª mensagem — sem
    # histórico, não tem o que forçar ainda.
    chat = FakeChatService()
    conversa = _montar_conversa(chat_service=chat)

    await conversa.responder("quero uma peça", uuid4(), CategoriaMensagem.CONSULTA_PECA)

    assert chat.forcar_recebidos == [False]


async def test_segunda_mensagem_sobre_peca_sem_consulta_real_forca_ferramenta():
    # Vazamento visto ao vivo: depois de idas e vindas, a IA "confirmou"
    # que uma peça existe/está em estoque sem NUNCA ter chamado
    # consultar_preco_peca. A partir da 2ª mensagem do cliente sobre o
    # assunto, sem nenhum "[peca_id:" no histórico ainda, a próxima
    # resposta tem que ser obrigatoriamente uma chamada de ferramenta.
    chat = FakeChatService()
    conversa = _montar_conversa(chat_service=chat)
    historico = [_mensagem_consulta_peca(), _mensagem_consulta_peca()]

    await conversa.responder(
        "é pra fan 160", uuid4(), CategoriaMensagem.CONSULTA_PECA, historico=historico
    )

    assert chat.forcar_recebidos == [True]


async def test_peca_ja_consultada_no_historico_nao_forca_ferramenta():
    # Assim que uma consulta real já aconteceu (ferramentas_chamadas
    # registrado no histórico — não o texto, que a IA reescreve/parafraseia
    # e não preserva marcador nenhum), a IA volta a ter liberdade de
    # responder em texto — ela já tem dado real pra trabalhar em cima.
    chat = FakeChatService()
    conversa = _montar_conversa(chat_service=chat)
    historico = [
        _mensagem_consulta_peca(
            resposta_ia="Temos o Paralama (Honda 2020-2025) por R$ 120,00, disponível.",
            ferramentas_chamadas=["consultar_preco_peca"],
        )
    ]

    await conversa.responder(
        "quero 1, retirada local", uuid4(), CategoriaMensagem.CONSULTA_PECA, historico=historico
    )

    assert chat.forcar_recebidos == [False]


async def test_limite_de_trocas_sem_resolucao_transfere_para_humano():
    # Nenhuma IA acerta 100% das vezes — depois de N (3, o padrão)
    # trocas seguidas sem nenhuma ação concluída, corta e transfere pra
    # humano SEM gastar mais uma chamada de API.
    chat = FakeChatService()
    conversa = _montar_conversa(chat_service=chat)
    historico = [_mensagem_consulta_peca() for _ in range(3)]

    resultado = await conversa.responder(
        "quero por 64 reais", uuid4(), CategoriaMensagem.CONSULTA_PECA, historico=historico
    )

    assert chat.ferramentas_recebidas == []  # IA nem chegou a ser chamada
    assert resultado.texto == MENSAGEM_LIMITE_TROCAS
    assert resultado.precisa_atendimento_humano is True
    assert resultado.motivo_atendimento == MotivoAtendimento.LIMITE_TROCAS_ATINGIDO


async def test_limite_de_trocas_reseta_apos_acao_concluida():
    # O contador conta só as trocas DESDE a última ação concluída — uma
    # compra/agendamento/cancelamento resolvido reseta a contagem pro
    # próximo assunto, mesmo que o histórico total seja longo.
    chat = FakeChatService()
    conversa = _montar_conversa(chat_service=chat)
    historico = [
        _mensagem_consulta_peca(),
        _mensagem_consulta_peca(),
        Mensagem(
            id=uuid4(),
            cliente_id=uuid4(),
            texto="1, retirada",
            categoria=CategoriaMensagem.CONSULTA_PECA,
            criado_em=datetime.now(timezone.utc),
            resposta_ia="Pedido #1 confirmado!",
            acao_finalizadora="criar_pedido",
        ),
        _mensagem_consulta_peca(),
    ]

    resultado = await conversa.responder(
        "quero outra peça", uuid4(), CategoriaMensagem.CONSULTA_PECA, historico=historico
    )

    # Só 1 troca não resolvida desde a ação concluída — não deveria
    # transferir, deveria ter chamado a IA normalmente.
    assert resultado.motivo_atendimento != MotivoAtendimento.LIMITE_TROCAS_ATINGIDO
    assert chat.ferramentas_recebidas != []
