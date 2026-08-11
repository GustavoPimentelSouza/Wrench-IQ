from collections import Counter
from dataclasses import dataclass
from datetime import date

from application.protocolo_repository import ProtocoloRepository
from application.reclassificacao_repository import ReclassificacaoRepository
from domain.especialidade import Especialidade


@dataclass
class TaxaPorEspecialidade:
    especialidade: Especialidade
    total_reclassificacoes: int


@dataclass
class RelatorioTaxaReclassificacao:
    periodo_inicio: date
    periodo_fim: date
    total_protocolos: int
    total_reclassificados: int
    # 0.0 quando não houve protocolo nenhum no período — evita divisão por
    # zero em vez de estourar exceção num relatório.
    taxa: float
    # Contado pela especialidade FINAL (pra onde o mecânico corrigiu) — é o
    # sinal de qual área a classificação automática mais erra.
    por_especialidade: list[TaxaPorEspecialidade]


# Nenhum classificador acerta 100% do volume real de mensagens — esse
# relatório é a métrica objetiva de quão certeira a classificação
# automática está sendo em produção (ver domain/reclassificacao_especialidade.py),
# usada pra decidir onde vale a pena investir em atalho determinístico na
# camada de palavra-chave/prompt (conversa_prompts.py) em vez de só confiar
# no modelo.
class RelatorioUseCases:
    def __init__(
        self,
        reclassificacao_repository: ReclassificacaoRepository,
        protocolo_repository: ProtocoloRepository,
    ):
        self._reclassificacoes = reclassificacao_repository
        self._protocolos = protocolo_repository

    async def taxa_reclassificacao(
        self, inicio: date, fim: date
    ) -> RelatorioTaxaReclassificacao:
        reclassificacoes = await self._reclassificacoes.listar_por_periodo(inicio, fim)
        total_protocolos = await self._protocolos.contar_por_periodo(inicio, fim)

        contagem: Counter[Especialidade] = Counter()
        for reclassificacao in reclassificacoes:
            contagem.update(reclassificacao.especialidades_finais)

        taxa = len(reclassificacoes) / total_protocolos if total_protocolos else 0.0
        return RelatorioTaxaReclassificacao(
            periodo_inicio=inicio,
            periodo_fim=fim,
            total_protocolos=total_protocolos,
            total_reclassificados=len(reclassificacoes),
            taxa=taxa,
            por_especialidade=[
                TaxaPorEspecialidade(especialidade=especialidade, total_reclassificacoes=total)
                for especialidade, total in contagem.most_common()
            ],
        )
