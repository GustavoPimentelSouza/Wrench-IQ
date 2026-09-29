import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from adapters.orm_models import Base

# Arquivo próprio (e não em orm_models.py) por dois motivos: orm_models.py
# já passou do limite de ~250 linhas, e a feature é temporária — sai
# inteira apagando este arquivo, sem mexer nos modelos permanentes.


class AvaliacaoTesteORM(Base):
    __tablename__ = "avaliacoes_teste"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # unique: uma avaliação por conversa. CASCADE: apagar o cliente de teste
    # leva a avaliação junto, sem travar a exclusão.
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    resultado: Mapped[str] = mapped_column(String, nullable=False)
    comentario: Mapped[str | None] = mapped_column(String, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
