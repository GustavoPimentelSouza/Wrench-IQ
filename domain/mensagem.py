import enum
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

# A classificação por IA (I/O, depende de rede) mora em
# application/classificacao_mensagem_service.py + adapters/groq_adapter.py,
# não aqui — domain fica só com o conceito puro de negócio.


class CategoriaMensagem(str, enum.Enum):
    """Categorias possíveis pra uma mensagem recebida do cliente."""

    CONSULTA_PECA = "consulta_peca"
    DUVIDA_GERAL = "duvida_geral"
    NAO_IDENTIFICADO = "nao_identificado"
    # dano_estrutural e reclamacao_sensivel: regras 1 e 4 do CLAUDE.md
    # (nunca orçamento automático / sempre cai pro humano).
    DANO_ESTRUTURAL = "dano_estrutural"
    AGENDAMENTO = "agendamento"
    STATUS_PROTOCOLO = "status_protocolo"
    RECLAMACAO_SENSIVEL = "reclamacao_sensivel"


class MotivoAtendimento(str, enum.Enum):
    """Por que uma mensagem caiu pro atendente humano — sem isso, falha
    técnica (ex: IA fora do ar) e reclamação de verdade apareciam idênticas
    na fila, e o atendente não tinha como saber qual é qual sem ler tudo."""

    FALHA_TECNICA = "falha_tecnica"
    RECLAMACAO_SENSIVEL = "reclamacao_sensivel"
    # A própria IA, no meio da conversa, decidiu que precisa de um humano
    # (ex: pedido fora do que ela sabe resolver) — diferente de reclamação
    # sensível, que é decidido antes de chamar a IA, pela classificação.
    TRANSFERENCIA_IA = "transferencia_ia"
    # Determinístico, decidido ANTES de chamar a IA nesse turno (ver
    # ConversaUseCases.responder) — quantas trocas seguidas sem nenhuma ação
    # concluída (criar_pedido, cancelar_pedido, agendar_visita) já
    # aconteceram passou do limite configurado (ConfiguracaoOficina.
    # limite_trocas_sem_resolucao). Cliente insistindo (ex: tentando
    # manipular preço) ou a IA capengando são os dois casos reais que isso
    # cobre — em ambos, continuar tentando sozinha só gasta chamada de API
    # e atrasa quem precisa de fato de um humano.
    LIMITE_TROCAS_ATINGIDO = "limite_trocas_atingido"


@dataclass
class Mensagem:
    id: UUID
    cliente_id: UUID
    texto: str
    categoria: CategoriaMensagem
    criado_em: datetime
    # Preenchida depois de criar a Mensagem, quando a IA gera a resposta
    # (ver ConversaUseCases) — é o que dá memória de conversa: sem isso, cada
    # mensagem do cliente é tratada como se fosse a primeira da conversa.
    resposta_ia: str | None = None
    # Regra 4 do CLAUDE.md: falha técnica ou reclamação sensível cai pro
    # atendente humano. Marcado automaticamente (ver webhook.py) quando a
    # categoria é reclamacao_sensivel, quando a IA falha tecnicamente, ou
    # quando a própria IA pede transferência (ver motivo_atendimento).
    precisa_atendimento_humano: bool = False
    motivo_atendimento: MotivoAtendimento | None = None
    atendimento_resolvido: bool = False
    # Nome da ferramenta que encerrou o turno (criar_pedido, cancelar_pedido,
    # agendar_visita, transferir_atendimento) quando a IA de fato executou
    # uma ação — None quando o turno só foi conversa, sem ação concluída.
    # Existe pra ConversaUseCases saber, no PRÓXIMO turno, que uma ação
    # acabou de ser concluída — sem isso, uma confirmação de encerramento
    # do cliente (ex: "só isso mesmo") logo depois de um pedido criado não
    # tinha como ser diferenciada de uma mensagem qualquer, e a IA podia
    # (já vimos acontecer) chamar criar_pedido de novo pra mesma compra.
    acao_finalizadora: str | None = None
    # URL da imagem enviada junto da resposta desse turno (se houve). Existe
    # pra ConversaUseCases conseguir checar, no PRÓXIMO turno, "essa imagem
    # já apareceu nessa conversa?" — sem isso, cada vez que a IA rechama
    # consultar_preco_peca pra confirmar a mesma peça (o que já vimos
    # acontecer), a mesma foto era reenviada, poluindo o chat sem
    # necessidade.
    imagem_url: str | None = None
    # Nomes das ferramentas chamadas nesse turno (ex: ["consultar_preco_peca"]),
    # gravado direto do que o código de fato executou — NUNCA inferido do
    # texto da resposta. Existe porque a IA reescreve/parafraseia o
    # resultado da ferramenta antes de responder ao cliente, e um texto
    # natural nunca preserva um marcador interno tipo "[peca_id: ...]" —
    # depender de achar esse marcador no histórico (ver ConversaUseCases)
    # concluía errado que "ainda não consultou nada" e forçava reconsultar
    # pra sempre, travando a venda antes de chegar em criar_pedido.
    ferramentas_chamadas: list[str] = field(default_factory=list)
