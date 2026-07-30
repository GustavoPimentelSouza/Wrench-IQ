import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class StatusProtocolo(str, enum.Enum):
    # Ordem de fluxo (ver application/protocolo_use_cases.py pra transições
    # válidas): AGUARDANDO_APROVACAO -> EM_EXECUCAO -> PRONTO, com CANCELADO
    # possível a partir dos dois primeiros. PRONTO e CANCELADO são estados
    # finais — não existe transição pra fora deles.
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    EM_EXECUCAO = "em_execucao"
    PRONTO = "pronto"
    CANCELADO = "cancelado"


@dataclass
class Protocolo:
    """Um Protocolo é a "ordem de serviço" — o registro de um veículo que
    entrou pra avaliação/conserto na oficina. Não confundir com Pedido
    (que é venda de peça): Protocolo é sobre serviço/mão de obra, e por
    regra de negócio (CLAUDE.md, regra 1) a IA nunca fecha orçamento de
    serviço sozinha — só classifica a categoria do problema e oferece
    agendamento de visita.
    """

    id: UUID
    cliente_id: UUID
    # Hoje é uma string livre (ex: "Onix 2022"), não uma referência pra uma
    # tabela de veículos estruturada — mesmo existindo uma entidade Veiculo
    # separada no projeto (domain/veiculo.py). É uma simplificação
    # deliberada: transformar isso numa FK quebraria o contrato de API e os
    # testes existentes, então ficou como próximo passo possível, não feito
    # ainda.
    veiculo: str
    categoria: str  # ex: "farol", "pintura", "dano_estrutural" — usado pra decidir se a IA pode agir ou só agendar
    status: StatusProtocolo
    criado_em: datetime
    numero: int | None = None  # número sequencial, gerado pelo banco (igual ao de Pedido)
    descricao: str | None = None
    # Referência opcional a um Usuario (que tenha papel=MECANICO) responsável
    # pelo serviço. É opcional de propósito — um protocolo pode nascer sem
    # mecânico designado ainda. Repara que NADA aqui garante que o UUID
    # aponte pra um usuário com o papel certo — essa validação simplesmente
    # não existe hoje (nem no domínio, nem no use case, nem no banco).
    mecanico_id: UUID | None = None
    # Atualizado automaticamente pelo banco (onupdate, ver ProtocoloORM) toda
    # vez que a linha muda — é None aqui só porque, igual numero, o valor
    # real só existe depois que o registro já foi salvo/atualizado no banco.
    atualizado_em: datetime | None = None
