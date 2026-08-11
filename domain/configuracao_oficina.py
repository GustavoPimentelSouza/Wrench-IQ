from dataclasses import dataclass
from datetime import time


@dataclass
class ConfiguracaoOficina:
    """Dados institucionais da oficina, usados pelo prompt da IA (pra ela
    parar de inventar coisa que não sabe — nome, endereço, horário, mensagem
    de encerramento). Sempre uma linha só no banco — não é por cliente nem
    por peça, é uma configuração global do negócio. Sábado e domingo podem
    ficar fechados (abertura/fechamento = None).
    """

    id: int
    nome_empresa: str
    horario_semana_abertura: time
    horario_semana_fechamento: time
    horario_sabado_abertura: time | None
    horario_sabado_fechamento: time | None
    horario_domingo_abertura: time | None
    horario_domingo_fechamento: time | None
    endereco: str | None = None
    mensagem_encerramento: str | None = None
    # Passado esse tempo do horário marcado sem o cliente aparecer, o
    # agendamento é liberado automaticamente e oferecido pro primeiro da
    # lista de espera daquela especialidade (ver
    # AgendamentoDisponibilidadeUseCases.liberar_no_shows). Configurável
    # porque o "tempo de tolerância razoável" varia de oficina pra oficina.
    tolerancia_no_show_minutos: int = 20
    # Quantas trocas seguidas com o cliente, sem nenhuma ação concluída
    # (pedido criado, agendamento marcado, cancelamento), até desistir de
    # deixar só a IA tentando e transferir pra atendente humano (ver
    # ConversaUseCases.responder). Existe porque a IA sozinha nunca acerta
    # 100% das vezes, e insistir sem limite só atrasa quem realmente
    # precisa de um humano (ou vira alvo de alguém tentando manipular a
    # conversa, ex: fingir ser "dono da oficina" pra forçar desconto).
    limite_trocas_sem_resolucao: int = 3
