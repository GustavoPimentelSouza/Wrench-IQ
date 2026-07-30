from datetime import datetime, timezone
from uuid import uuid4

from adapters.seguranca import criar_hash_senha, criar_token_acesso, verificar_senha
from application.usuario_repository import UsuarioRepository
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
        # As 3 condições do "or" abaixo são checadas em sequência, mas
        # Python usa short-circuit: se `usuario is None` já for True, nem
        # tenta acessar usuario.ativo (que quebraria com AttributeError
        # num None). É por isso que a ordem importa aqui.
        #
        # Detalhe de segurança sutil: as 3 causas de falha (usuário não
        # existe / está desativado / senha errada) levantam o MESMO erro
        # genérico (CredenciaisInvalidasError), sem distinguir qual foi.
        # Isso evita "enumeration attack" — um atacante não consegue
        # descobrir se um email existe no sistema só testando o login.
        if (
            usuario is None
            or not usuario.ativo
            or not verificar_senha(senha, usuario.senha_hash)
        ):
            raise CredenciaisInvalidasError()
        token = criar_token_acesso(usuario.id, usuario.papel)
        return token, usuario

    async def registrar(
        self, nome: str, email: str, senha: str, papel: PapelUsuario
    ) -> Usuario:
        # Quem pode chamar isso já é filtrado antes de chegar aqui (rota
        # /auth/registrar exige exigir_admin) — mas mesmo assim o use case
        # confere email duplicado por conta própria, porque um use case não
        # deveria confiar cegamente que quem chamou já validou tudo.
        existente = await self._repository.buscar_por_email(email)
        if existente is not None:
            raise EmailJaCadastradoError()
        usuario = Usuario(
            id=uuid4(),
            nome=nome,
            email=email,
            # A senha em texto puro (`senha`) nunca é guardada em lugar
            # nenhum — só passa pela função de hash e é descartada. A
            # partir daqui só existe `senha_hash`.
            senha_hash=criar_hash_senha(senha),
            papel=papel,
            ativo=True,
            criado_em=datetime.now(timezone.utc),
        )
        return await self._repository.criar(usuario)
