import { useEffect, useState } from "react";
import { MetricCard } from "../components/MetricCard";
import { ProtocoloCard } from "../components/ProtocoloCard";
import { METRICAS_MOCK } from "../mocks/protocolos";
import { listarProtocolos } from "../services/protocoloService";
import type { Protocolo, StatusProtocolo } from "../types/protocolo";

const COLUNAS: { status: StatusProtocolo; titulo: string }[] = [
  { status: "em_execucao", titulo: "Em execução" },
  { status: "aguardando_aprovacao", titulo: "Aguardando aprovação" },
  { status: "pronto", titulo: "Pronto" },
];

export function PainelPage() {
  const [protocolos, setProtocolos] = useState<Protocolo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    listarProtocolos()
      .then(setProtocolos)
      .catch(() => setErro("Não foi possível carregar os protocolos."))
      .finally(() => setCarregando(false));
  }, []);

  return (
    <div>
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard
          titulo="Protocolos abertos"
          valor={String(METRICAS_MOCK.protocolosAbertos)}
        />
        <MetricCard
          titulo="Peças com estoque baixo"
          valor={String(METRICAS_MOCK.pecasComEstoqueBaixo)}
          tonalidade="alerta"
        />
        <MetricCard titulo="Faturamento hoje" valor={METRICAS_MOCK.faturamentoHoje} />
      </div>

      <h2 className="mb-4 text-lg font-semibold text-gray-900">Protocolos</h2>

      {erro && <p className="text-sm text-red-700">{erro}</p>}
      {carregando && !erro && <p className="text-sm text-gray-500">Carregando...</p>}

      {!carregando && !erro && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {COLUNAS.map((coluna) => (
            <div key={coluna.status}>
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
                {coluna.titulo}
              </p>
              <div className="flex flex-col gap-3">
                {protocolos
                  .filter((protocolo) => protocolo.status === coluna.status)
                  .map((protocolo) => (
                    <ProtocoloCard key={protocolo.id} protocolo={protocolo} />
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
