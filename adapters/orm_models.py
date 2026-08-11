import uuid
from datetime import datetime, time, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Table,
    Time,
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from domain.usuario import PapelUsuario


class Base(DeclarativeBase):
    pass


class PecaORM(Base):
    __tablename__ = "pecas"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String, nullable=False)
    marca_modelo_compativel: Mapped[str] = mapped_column(String, nullable=False)
    ano_compativel: Mapped[str] = mapped_column(String, nullable=False)
    preco: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantidade_estoque: Mapped[int] = mapped_column(Integer, nullable=False)
    imagem_url: Mapped[str | None] = mapped_column(String, nullable=True)
    quantidade_minima: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cor: Mapped[str | None] = mapped_column(String, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # Vetor de "nome + marca_modelo_compativel + ano_compativel + cor",
    # gerado ao criar/atualizar a peça (ver sqlalchemy_peca_repository.py) —
    # é o que permite buscar por significado, não só por substring literal.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)


class UsuarioORM(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    papel: Mapped[PapelUsuario] = mapped_column(
        SQLEnum(
            PapelUsuario,
            name="papel_usuario",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class MensagemORM(Base):
    __tablename__ = "mensagens"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    texto: Mapped[str] = mapped_column(String, nullable=False)
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resposta_ia: Mapped[str | None] = mapped_column(String, nullable=True)
    precisa_atendimento_humano: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    motivo_atendimento: Mapped[str | None] = mapped_column(String, nullable=True)
    atendimento_resolvido: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    acao_finalizadora: Mapped[str | None] = mapped_column(String, nullable=True)
    imagem_url: Mapped[str | None] = mapped_column(String, nullable=True)


class ClienteORM(Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String, nullable=False)
    telefone: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco: Mapped[str | None] = mapped_column(String, nullable=True)
    cpf_cnpj: Mapped[str | None] = mapped_column(String, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ProtocoloORM(Base):
    __tablename__ = "protocolos"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    numero: Mapped[int] = mapped_column(
        Integer, Identity(), unique=True, nullable=False
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    veiculo: Mapped[str] = mapped_column(String, nullable=False)
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    descricao: Mapped[str | None] = mapped_column(String, nullable=True)
    mecanico_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    valor_orcamento: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    motivo_cancelamento: Mapped[str | None] = mapped_column(String, nullable=True)


class PedidoORM(Base):
    __tablename__ = "pedidos"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    numero: Mapped[int] = mapped_column(
        Integer, Identity(), unique=True, nullable=False
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    peca_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pecas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tipo_entrega: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    endereco_entrega: Mapped[str | None] = mapped_column(String, nullable=True)
    link_pagamento: Mapped[str | None] = mapped_column(String, nullable=True)
    entregue_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class VeiculoORM(Base):
    __tablename__ = "veiculos"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    marca: Mapped[str] = mapped_column(String, nullable=False)
    modelo: Mapped[str] = mapped_column(String, nullable=False)
    ano: Mapped[str] = mapped_column(String, nullable=False)
    placa: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AgendamentoORM(Base):
    __tablename__ = "agendamentos"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    descricao: Mapped[str | None] = mapped_column(String, nullable=True)


class MovimentacaoEstoqueORM(Base):
    __tablename__ = "movimentacoes_estoque"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    peca_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pecas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ConfiguracaoOficinaORM(Base):
    __tablename__ = "configuracao_oficina"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome_empresa: Mapped[str] = mapped_column(String, nullable=False)
    horario_semana_abertura: Mapped[time] = mapped_column(Time, nullable=False)
    horario_semana_fechamento: Mapped[time] = mapped_column(Time, nullable=False)
    horario_sabado_abertura: Mapped[time | None] = mapped_column(Time, nullable=True)
    horario_sabado_fechamento: Mapped[time | None] = mapped_column(Time, nullable=True)
    horario_domingo_abertura: Mapped[time | None] = mapped_column(Time, nullable=True)
    horario_domingo_fechamento: Mapped[time | None] = mapped_column(Time, nullable=True)
    endereco: Mapped[str | None] = mapped_column(String, nullable=True)
    mensagem_encerramento: Mapped[str | None] = mapped_column(String, nullable=True)
    tolerancia_no_show_minutos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20, server_default="20"
    )
    limite_trocas_sem_resolucao: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )


class ItemAdicionalProtocoloORM(Base):
    __tablename__ = "itens_adicionais_protocolo"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    protocolo_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("protocolos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    descricao: Mapped[str] = mapped_column(String, nullable=False)
    peca_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pecas.id", ondelete="RESTRICT"),
        nullable=True,
    )
    valor: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class NotificacaoORM(Base):
    __tablename__ = "notificacoes"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    mensagem: Mapped[str] = mapped_column(String, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    enviada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    enviada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ListaEsperaAgendamentoORM(Base):
    __tablename__ = "lista_espera_agendamento"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    especialidade: Mapped[str] = mapped_column(String, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    atendido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class ReclassificacaoEspecialidadeORM(Base):
    __tablename__ = "reclassificacoes_especialidade"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    protocolo_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("protocolos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Listas guardadas como string separada por vírgula (ex:
    # "funilaria_pintura,eletrica") — é um registro histórico/log, não uma
    # relação N:N consultada por item; volume de reclassificação é baixo,
    # então não compensa outra tabela de junção só pra isso (ver
    # adapters/sqlalchemy_reclassificacao_repository.py).
    especialidades_originais: Mapped[str] = mapped_column(String, nullable=False)
    especialidades_finais: Mapped[str] = mapped_column(String, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# As 3 tabelas abaixo são N:N puras (só as duas colunas da relação, sem
# dado próprio) — por isso são Table simples, não uma classe ORM mapeada
# como as entidades acima. CASCADE em todas: se o registro pai (protocolo,
# agendamento ou usuário) for excluído, as linhas de especialidade dele não
# ficam órfãs no banco.
protocolo_especialidades = Table(
    "protocolo_especialidades",
    Base.metadata,
    Column(
        "protocolo_id",
        PG_UUID(as_uuid=True),
        ForeignKey("protocolos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("especialidade", String, primary_key=True),
)

agendamento_especialidades = Table(
    "agendamento_especialidades",
    Base.metadata,
    Column(
        "agendamento_id",
        PG_UUID(as_uuid=True),
        ForeignKey("agendamentos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("especialidade", String, primary_key=True),
)

mecanico_especialidades = Table(
    "mecanico_especialidades",
    Base.metadata,
    Column(
        "usuario_id",
        PG_UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("especialidade", String, primary_key=True),
)
