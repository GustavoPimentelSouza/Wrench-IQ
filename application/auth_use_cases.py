from datetime import datetime, timezone
from uuid import uuid4

from adapters.seguranca import criar_hash_senha, criar_token_acesso, verificar_senha
from application.usuario_repository import UsuarioRepository
from domain.especialidade import Especialidade
from domain.usuario import PapelUsuario, Usuario


class CredenciaisInvalidasError(Exception):
    pass


class EmailJaCadastradoError(Exception):
    pass


class AuthUseCases:
    def __init__(self, repository: UsuarioRepository):
        self._repository = repository

    async def login(self, email: str, senha: str) -> tuple[str, Usuario]:
        usuario = await self._repository.buscar_por_email(email)
        # As 3 causas de falha levantam o mesmo erro genérico de propósito
        # — evita enumeration attack (descobrir se um email existe testando login).
        if (
            usuario is None
            or not usuario.ativo
            or not verificar_senha(senha, usuario.senha_hash)
        ):
            raise CredenciaisInvalidasError()
        token = criar_token_acesso(usuario.id, usuario.papel)
        return token, usuario

    async def registrar(
        self,
        nome: str,
        email: str,
        senha: str,
        papel: PapelUsuario,
        especialidades: list[Especialidade] | None = None,
    ) -> Usuario:
        existente = await self._repository.buscar_por_email(email)
        if existente is not None:
            raise EmailJaCadastradoError()
        usuario = Usuario(
            id=uuid4(),
            nome=nome,
            email=email,
            senha_hash=criar_hash_senha(senha),
            papel=papel,
            ativo=True,
            criado_em=datetime.now(timezone.utc),
            # Só faz sentido pra papel=MECANICO — pra ADMIN/ATENDENTE fica
            # sempre vazio, mesmo que alguém mande algo (não é validado
            # aqui pra não ter que dar erro à toa; simplesmente não é usado).
            especialidades=especialidades or [] if papel == PapelUsuario.MECANICO else [],
        )
        return await self._repository.criar(usuario)
