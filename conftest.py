import os
from pathlib import Path

_ENV_TEST_FILE = Path(__file__).parent / ".env.test"


def _carregar_env_test() -> None:
    if not _ENV_TEST_FILE.exists():
        return
    for linha in _ENV_TEST_FILE.read_text().splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip())


_carregar_env_test()
