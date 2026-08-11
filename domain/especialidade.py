import enum

# Departamento/área de atuação de um mecânico — usado pra filtrar quem pode
# atender um Protocolo/Agendamento, e pra classificar o tipo de serviço que
# a IA agenda. Compartilhado entre Usuario, Protocolo e Agendamento, por
# isso mora num arquivo próprio (não pertence a nenhum dos três sozinho).
# Agrupado por "quem realmente faz esse serviço na prática", não por nome
# bonito — funilaria/pintura/martelinho de ouro é sempre a mesma pessoa
# numa oficina pequena/média, por isso ficam juntos numa especialidade só.


class Especialidade(str, enum.Enum):
    FUNILARIA_PINTURA = "funilaria_pintura"  # lanternagem, funilaria, martelinho de ouro, pintura, polimento
    ELETRICA = "eletrica"  # sistema elétrico, injeção eletrônica, bateria, diagnóstico
    MECANICA_GERAL = "mecanica_geral"  # motor, câmbio, embreagem, suspensão, freios, revisão
    MONTAGEM = "montagem"  # pneu, alinhamento, balanceamento, instalação de peça avulsa
    # Casos em que nem o cliente nem a IA conseguem inferir a área com
    # segurança (ex: "meu carro morre sem motivo aparente"). Forçar uma
    # especialidade errada aqui é PIOR do que admitir incerteza: manda o
    # mecânico errado, atrasa o atendimento de verdade, e ainda suja o
    # histórico de reclassificação (domain/reclassificacao_especialidade.py)
    # com um "erro" que na origem já era um chute — por isso é um valor de
    # verdade do enum, persistido como está, nunca convertido
    # silenciosamente na hora de criar o Agendamento/Protocolo.
    INDEFINIDO = "indefinido"


def normalizar_especialidades(brutas: list[str]) -> list[Especialidade]:
    # dict.fromkeys em vez de set(): remove duplicata mantendo a ordem
    # original — importante pra não embaralhar a lista que a IA mandou.
    return list(dict.fromkeys(Especialidade(bruta) for bruta in brutas))


# Só usado na hora de checar disponibilidade/qualificação de mecânico — não
# existe (nem faria sentido existir) um mecânico "de indefinido" cadastrado,
# então pra esse fim (e só pra esse fim) INDEFINIDO conta como
# MECANICA_GERAL: o generalista faz a triagem presencial e reclassifica
# depois (ver ProtocoloUseCases.reclassificar_especialidade). O dado bruto
# (indefinido) continua intacto no registro — só a busca de disponibilidade
# traduz, na hora da consulta, nunca na hora de salvar.
def especialidade_para_disponibilidade(especialidade: Especialidade) -> Especialidade:
    if especialidade == Especialidade.INDEFINIDO:
        return Especialidade.MECANICA_GERAL
    return especialidade


def especialidades_para_disponibilidade(especialidades: list[Especialidade]) -> list[Especialidade]:
    return list(dict.fromkeys(especialidade_para_disponibilidade(e) for e in especialidades))
