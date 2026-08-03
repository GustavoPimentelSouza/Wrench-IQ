import { useEffect, useState } from "react";
import { MetricCard } from "../components/MetricCard";
import { ProtocoloCard } from "../components/ProtocoloCard";
import { listarPecas } from "../services/pecaService";
import { listarProtocolos } from "../services/protocoloService";
import type { Peca } from "../types/peca";
import type { Protocolo, StatusProtocolo } from "../types/protocolo";

const COLUNAS: { status: StatusProtocolo; titulo: string }[] = [
  { status: "em_execucao", titulo: "Em execução" },
  { status: "aguardando_aprovacao", titulo: "Aguardando aprovação" },
  { status: "pronto", titulo: "Pronto" },
];

function contarEstoqueBaixo(pecas: Peca[]): number {
  return pecas.filter(
    (peca) => peca.quantidade_minima > 0 && peca.quantidade_estoque <= peca.quantidade_minima,
  ).length;
}

export function PainelPage() {
  const [protocolos, setProtocolos] = useState<Protocolo[]>([]);
  const [pecas, setPecas] = useState<Peca[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listarProtocolos(), listarPecas()])
      .then(([protocolosCarregados, pecasCarregadas]) => {
        setProtocolos(protocolosCarregados);
        setPecas(pecasCarregadas);
      })
      .catch(() => setErro("Não foi possível carregar os dados do painel."))
      .finally(() => setCarregando(false));
  }, []);

  const protocolosAbertos = protocolos.filter((p) => p.status !== "cancelado").length;

  return (
    <div>
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <MetricCard titulo="Protocolos abertos" valor={String(protocolosAbertos)} />
        <MetricCard
          titulo="Peças com estoque baixo"
          valor={String(contarEstoqueBaixo(pecas))}
          tonalidade="alerta"
        />
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
