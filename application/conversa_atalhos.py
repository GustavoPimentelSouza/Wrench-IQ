from domain.configuracao_oficina import ConfiguracaoOficina
from domain.mensagem import Mensagem

from application.conversa_prompts import (
    MENSAGEM_ENCERRAMENTO_PADRAO,
    MENSAGEM_SAUDACAO,
    eh_confirmacao_encerramento,
    eh_saudacao,
)

# Ferramentas que representam uma transação concluída de verdade (algo que
# não pode ser repetido sem querer). transferir_atendimento fica de fora —
# depois de um handoff pra humano não faz sentido "fechar a conversa" pela
# IA, então não participa dessa checagem.
ACOES_TRANSACIONAIS = {"criar_pedido", "cancelar_pedido", "agendar_visita"}


def resposta_saudacao_pura(mensagem: str) -> str | None:
    """Saudação pura (ex: "oi", "bom dia") não precisa da IA — determinístico,
    sem custo, e sem depender do modelo "decidir" responder algo tão simples.
    None quando não é saudação pura, pra quem chama seguir pro resto do
    pipeline."""
    return MENSAGEM_SAUDACAO if eh_saudacao(mensagem) else None


def resposta_confirmacao_encerramento(
    mensagem: str, historico: list[Mensagem], configuracao: ConfiguracaoOficina
) -> str | None:
    """Alta confiança, decidido sem chamar o modelo: cliente confirmando que
    não quer mais nada, logo depois de uma ação concluída (pedido criado,
    agendamento marcado, etc.). Já vimos o modelo, nesse exato cenário,
    chamar criar_pedido de novo pra mesma compra em vez de encerrar — não é
    algo que deva depender dele acertar toda vez."""
    se_encerrando = (
        historico
        and historico[-1].acao_finalizadora in ACOES_TRANSACIONAIS
        and eh_confirmacao_encerramento(mensagem)
    )
    if not se_encerrando:
        return None
    return configuracao.mensagem_encerramento or MENSAGEM_ENCERRAMENTO_PADRAO


def contar_trocas_sem_resolucao(historico: list[Mensagem]) -> int:
    """Trocas seguidas sem nenhuma ação concluída (criar_pedido,
    cancelar_pedido, agendar_visita) — usado pra decidir quando desistir de
    deixar só a IA tentando e transferir pra atendente humano (ver
    ConfiguracaoOficina.limite_trocas_sem_resolucao). Reseta sozinho:
    acao_finalizadora inclui transferir_atendimento, então depois de um
    handoff a contagem volta a zero pro próximo assunto."""
    trocas_sem_resolucao = 0
    for anterior in reversed(historico):
        if anterior.acao_finalizadora is not None:
            break
        trocas_sem_resolucao += 1
    return trocas_sem_resolucao
