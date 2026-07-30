import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# Este é um arquivo de "domain" — regra pura, sem banco, sem HTTP, sem nada
# externo. É por isso que só tem stdlib importada acima (enum, dataclasses,
# datetime, uuid). Se algum dia alguém precisar importar SQLAlchemy ou FastAPI
# aqui, é sinal de que o código está no lugar errado da arquitetura.
#
# A classificação por palavra-chave que existia aqui (classificar_mensagem +
# as listas _PALAVRAS_*) foi removida: agora quem decide a categoria é uma
# chamada de IA (Groq), que depende de rede/chave de API — ou seja, é I/O,
# não pode morar no domain. A interface pra isso
# (ClassificadorDeMensagem) está em
# application/classificacao_mensagem_service.py, e a implementação concreta
# em adapters/groq_adapter.py. O que continua aqui é só o que é
# genuinamente conceito de negócio: quais categorias existem, e o formato
# de uma Mensagem.


class CategoriaMensagem(str, enum.Enum):
    """As categorias possíveis pra uma mensagem recebida do cliente.

    Herdar de `str` além de `enum.Enum` é um truque comum: o valor
    (CategoriaMensagem.CONSULTA_PECA) se comporta como string de verdade
    ("consulta_peca") na hora de salvar no banco ou serializar em JSON,
    sem precisar converter manualmente toda hora.
    """

    CONSULTA_PECA = "consulta_peca"
    DUVIDA_GERAL = "duvida_geral"
    NAO_IDENTIFICADO = "nao_identificado"
    # Categorias que mapeiam direto pras regras de negócio do CLAUDE.md:
    # dano estrutural nunca recebe orçamento da IA, só oferece agendamento
    # de visita (regra 1); reclamação sensível cai sempre pro atendente
    # humano (regra 4, mesmo mecanismo de fallback de falha técnica).
    DANO_ESTRUTURAL = "dano_estrutural"
    AGENDAMENTO = "agendamento"
    STATUS_PROTOCOLO = "status_protocolo"
    RECLAMACAO_SENSIVEL = "reclamacao_sensivel"


@dataclass
class Mensagem:
    """A entidade de domínio. Repara que é só dado (sem métodos, sem lógica
    aqui dentro) — quem decide a categoria é o ClassificadorDeMensagem,
    chamado pelo caso de uso (application/mensagem_use_cases.py) antes de
    montar essa classe. Isso mantém a entidade simples e fácil de testar.

    Essa classe NÃO é a tabela do banco — a tabela real (com SQLAlchemy) é
    `MensagemORM`, em adapters/orm_models.py. São duas classes separadas de
    propósito: essa aqui não sabe nada sobre "banco de dados", só representa
    o conceito de negócio "uma mensagem recebida de um cliente".
    """

    id: UUID
    cliente_id: UUID  # a quem essa mensagem pertence (FK conceitual pro Cliente)
    texto: str  # o conteúdo bruto que o cliente mandou
    categoria: CategoriaMensagem  # resultado do ClassificadorDeMensagem
    criado_em: datetime
