from datetime import datetime, timezone

# Estado em memória (só vale pra essa instância do processo, não sobrevive
# restart nem escala pra múltiplos workers) — criado só pra dar visibilidade
# de DEV quando o classificador cai no fallback silencioso (ver
# GroqClassificador.classificar). Sem isso, uma falha real (ex: modelo
# descontinuado pela Groq, como já aconteceu com o llama-3.1-8b-instant)
# passa despercebida até alguém notar comportamento estranho na prática.
_ultima_falha_classificacao: datetime | None = None


def registrar_falha_classificacao() -> None:
    global _ultima_falha_classificacao
    _ultima_falha_classificacao = datetime.now(timezone.utc)


def ultima_falha_classificacao() -> datetime | None:
    return _ultima_falha_classificacao
