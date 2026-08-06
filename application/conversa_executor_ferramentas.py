from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from application.agendamento_use_cases import AgendamentoUseCases
from application.chat_service import ChamadaFerramenta
from application.conversa_ferramentas import endereco_parece_valido
from application.peca_repository import PecaRepository
from application.pedido_use_cases import (
    EnderecoObrigatorioError,
    EstoqueInsuficienteError,
    PecaNaoEncontradaError,
    PedidoUseCases,
    TransicaoInvalidaError,
)
from application.protocolo_use_cases import ProtocoloUseCases
from domain.agendamento import Agendamento, StatusAgendamento
from domain.mensagem import MotivoAtendimento
from domain.pedido import TipoEntrega
from domain.peca import Peca
from domain.protocolo import StatusProtocolo


def _escolher_por_cor(pecas: list[Peca], termo_busca: str) -> Peca:
    # buscar_por_nome_aproximado ordena por proximidade semântica GERAL do
    # texto, não por cor especificamente — então a peça com a cor certa
    # pode vir em 2º, 3º lugar, não em pecas[0]. Sem essa checagem, cadastrar
    # uma variante de cor no futuro não adiantaria nada: a IA nunca chegaria
    # a ver essa peça, e diria "não temos essa cor" com a peça certa ali do
    # lado, só porque não era a mais próxima na busca geral.
    termo_normalizado = termo_busca.lower()
    for peca in pecas:
        if peca.cor and peca.cor.lower() in termo_normalizado:
            return peca
    return pecas[0]


class ExecutorFerramentasConversa:
    """O que cada ferramenta chamada pela IA faz de verdade — acesso a
    banco/repositórios. ConversaUseCases cuida só da orquestração (categoria,
    prompt, loop de tool calling); esse executor não sabe nada sobre isso,
    só recebe "chamou X com esses argumentos" e devolve o resultado.
    """

    def __init__(
        self,
        peca_repository: PecaRepository,
        pedido_use_cases: PedidoUseCases,
        agendamento_use_cases: AgendamentoUseCases,
        protocolo_use_cases: ProtocoloUseCases,
    ):
        self._pecas = peca_repository
        self._pedidos = pedido_use_cases
        self._agendamentos = agendamento_use_cases
        self._protocolos = protocolo_use_cases

    async def executar(
        self, chamada: ChamadaFerramenta, cliente_id: UUID
    ) -> tuple[str, str | None, bool, MotivoAtendimento | None]:
        if chamada.nome == "consultar_preco_peca":
            texto, url = await self._consultar_preco_peca(chamada.argumentos)
            return texto, url, False, None
        if chamada.nome == "criar_pedido":
            texto, sucesso = await self._criar_pedido(chamada.argumentos, cliente_id)
            return texto, None, sucesso, None
        if chamada.nome == "cancelar_pedido":
            texto, sucesso = await self._cancelar_pedido(chamada.argumentos, cliente_id)
            return texto, None, sucesso, None
        if chamada.nome == "consultar_status_protocolo":
            texto = await self._consultar_status_protocolo(chamada.argumentos, cliente_id)
            return texto, None, False, None
        if chamada.nome == "agendar_visita":
            return await self._agendar_visita(chamada.argumentos, cliente_id), None, False, None
        if chamada.nome == "transferir_atendimento":
            texto = self._transferir_atendimento()
            return texto, None, True, MotivoAtendimento.TRANSFERENCIA_IA
        return "Ferramenta desconhecida.", None, False, None

    def _transferir_atendimento(self) -> str:
        # Texto fixo pro cliente — o campo "motivo" que a IA preenche não
        # aparece aqui de propósito (isso vira resposta_ia, que é enviado
        # pro cliente; não dá pra vazar anotação interna nessa mensagem).
        # Por enquanto só a categoria (motivo_atendimento=TRANSFERENCIA_IA)
        # chega até a tela de Atendimento — o texto livre da IA ainda não
        # tem onde ser guardado; ficaria pra um campo novo, se um dia fizer falta.
        return (
            "Entendido! Vou te transferir para um atendente humano, que já "
            "vai continuar o atendimento. Só um momento, por favor."
        )

    async def _agendar_visita(self, argumentos: dict[str, Any], cliente_id: UUID) -> str:
        try:
            data_hora = datetime.fromisoformat(argumentos["data_hora"])
            if data_hora.tzinfo is None:
                data_hora = data_hora.replace(tzinfo=timezone.utc)
            agendamento = await self._agendamentos.criar(
                Agendamento(
                    id=uuid4(),
                    cliente_id=cliente_id,
                    data_hora=data_hora,
                    status=StatusAgendamento.AGENDADO,
                    criado_em=datetime.now(timezone.utc),
                    descricao=argumentos.get("descricao"),
                )
            )
        except ValueError as erro:
            return f"Não foi possível agendar: {erro}. Pergunte ao cliente uma data válida, no futuro."

        data_formatada = agendamento.data_hora.strftime("%d/%m/%Y às %H:%M")
        return (
            f"Visita agendada para {data_formatada}. Informe ao cliente que um "
            "mecânico vai avaliar o dano presencialmente e que não é possível "
            "estimar valor de conserto pelo chat."
        )

    async def _consultar_preco_peca(self, argumentos: dict[str, Any]) -> tuple[str, str | None]:
        termo = argumentos["nome"]
        pecas = await self._pecas.buscar_por_nome_aproximado(termo)
        if not pecas:
            return (
                "Nenhuma peça parecida encontrada no catálogo. Pergunte ao "
                "cliente o nome da peça de outro jeito.",
                None,
            )

        # Busca semântica sempre devolve o candidato mais próximo (nunca uma
        # garantia exata) — por isso sempre pede confirmação, em vez de tentar
        # adivinhar "confiança" checando palavra por palavra (isso não existe
        # mais com embeddings; a peça pode ser a certa mesmo sem nenhuma
        # palavra em comum com o que o cliente digitou).
        peca = _escolher_por_cor(pecas, termo)
        disponibilidade = "disponível" if peca.quantidade_estoque > 0 else "sem estoque no momento"
        # Cor só entra na frase quando a peça realmente tem uma cadastrada —
        # nunca deixa a IA sem dado nenhum sobre cor (só teria como inventar).
        cor_info = f", cor {peca.cor}" if peca.cor else ", sem variação de cor cadastrada"
        texto = (
            f"Peça mais parecida encontrada: {peca.nome} ({peca.marca_modelo_compativel}, "
            f"{peca.ano_compativel}{cor_info}): R$ {peca.preco}, {disponibilidade}. "
            f"[peca_id: {peca.id}] Confirme com o cliente se é essa a peça certa "
            "antes de fechar qualquer venda."
        )
        return texto, peca.imagem_url

    async def _criar_pedido(self, argumentos: dict[str, Any], cliente_id: UUID) -> tuple[str, bool]:
        try:
            tipo_entrega = TipoEntrega(argumentos["tipo_entrega"])
            endereco = argumentos.get("endereco_entrega")
            if tipo_entrega == TipoEntrega.ENVIO_REMOTO and not endereco_parece_valido(endereco):
                return (
                    "Endereço de entrega ausente ou incompleto — pergunte ao "
                    "cliente o endereço completo (rua, número, bairro, cidade) "
                    "e só chame essa ferramenta de novo depois que ele responder.",
                    False,
                )

            pedido = await self._pedidos.criar(
                cliente_id=cliente_id,
                peca_id=UUID(argumentos["peca_id"]),
                quantidade=int(argumentos["quantidade"]),
                tipo_entrega=tipo_entrega,
                endereco_entrega=endereco,
            )
        except PecaNaoEncontradaError:
            return "peca_id inválido — chame consultar_preco_peca de novo antes de criar o pedido.", False
        except EstoqueInsuficienteError:
            return "Estoque insuficiente pra essa quantidade. Avise o cliente.", False
        except EnderecoObrigatorioError:
            return "Faltou o endereço de entrega — pergunte ao cliente antes de tentar de novo.", False
        except ValueError:
            return "peca_id ou tipo_entrega inválido — chame consultar_preco_peca de novo.", False

        # Texto já pronto pro cliente (não é mais só um resumo pra IA
        # reescrever) — número do pedido e valor são exatamente o que o
        # funcionário vai conferir no balcão, não pode depender da IA
        # parafrasear certo.
        peca = await self._pecas.buscar_por_id(pedido.peca_id)
        nome_peca = peca.nome if peca else "peça"
        texto = f"Pedido #{pedido.numero} confirmado! {nome_peca} — R$ {pedido.valor_total}."
        if pedido.tipo_entrega == TipoEntrega.ENVIO_REMOTO:
            texto += (
                f" Link de pagamento: {pedido.link_pagamento}. Você tem 7 dias de direito "
                "de arrependimento após a entrega, conforme o CDC."
            )
        else:
            texto += " Pode retirar na loja e pagar presencialmente na hora."
        # Sem isso, a conversa "morria" logo após confirmar — o cliente não
        # era convidado a continuar comprando, nem tinha um jeito claro de
        # encerrar. Pergunta as duas coisas juntas: a resposta do cliente
        # já dá pra IA decidir no próximo turno (ver _PROMPT_BASE).
        texto += " Posso ajudar com mais alguma coisa, ou posso finalizar por aqui?"
        return texto, True

    async def _cancelar_pedido(self, argumentos: dict[str, Any], cliente_id: UUID) -> tuple[str, bool]:
        numero = argumentos.get("numero")
        # Busca só entre os pedidos DESSE cliente — nunca por ID direto, pra
        # não deixar cancelar pedido de outra pessoa só chutando um número.
        pedidos_do_cliente = await self._pedidos.listar_por_cliente(cliente_id, limit=200)
        pedido = next((p for p in pedidos_do_cliente if p.numero == numero), None)
        if pedido is None:
            return f"Não encontrei nenhum pedido #{numero} pra esse cliente. Confirme o número.", False

        try:
            cancelado = await self._pedidos.cancelar(pedido.id)
        except TransicaoInvalidaError:
            return (
                f"Pedido #{numero} não pode mais ser cancelado (já foi entregue ou já "
                "está cancelado). Transfira pro atendente se o cliente insistir.",
                False,
            )
        return f"Pedido #{cancelado.numero} cancelado com sucesso. O estoque já foi devolvido.", True

    async def _consultar_status_protocolo(self, argumentos: dict[str, Any], cliente_id: UUID) -> str:
        numero = argumentos.get("numero")
        # Mesma regra do cancelar_pedido: busca só entre os protocolos DESSE
        # cliente, nunca por ID direto — não pode revelar status de
        # protocolo de outra pessoa só porque alguém chutou um número.
        protocolos_do_cliente = await self._protocolos.listar_por_cliente(cliente_id)
        protocolo = next((p for p in protocolos_do_cliente if p.numero == numero), None)
        if protocolo is None:
            return f"Não encontrei nenhum protocolo #{numero} pra esse cliente. Confirme o número."

        status_legivel = {
            StatusProtocolo.AGUARDANDO_APROVACAO: "aguardando aprovação do orçamento",
            StatusProtocolo.EM_EXECUCAO: "em execução",
            StatusProtocolo.PRONTO: "pronto pra retirada",
            StatusProtocolo.CANCELADO: "cancelado",
        }[protocolo.status]
        texto = f"Protocolo #{protocolo.numero} ({protocolo.veiculo}): {status_legivel}."
        # Só inclui valor se já existir — regra 1 do CLAUDE.md continua "a "
        # IA nunca fecha orçamento sozinha"; aqui só repassa um valor que um
        # mecânico humano já definiu antes (ver ProtocoloUseCases.aprovar).
        if protocolo.valor_orcamento is not None:
            texto += f" Valor do orçamento: R$ {protocolo.valor_orcamento}."
        return texto
