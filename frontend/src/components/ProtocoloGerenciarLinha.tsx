import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  aprovarProtocolo,
  atualizarProtocolo,
  cancelarProtocolo,
  concluirProtocolo,
} from "../services/protocoloService";
import type { Protocolo } from "../types/protocolo";
import { ProtocoloCard } from "./ProtocoloCard";

const STATUS_LABELS: Record<Protocolo["status"], string> = {
  aguardando_aprovacao: "Aguardando aprovação",
  em_execucao: "Em execução",
  pronto: "Pronto",
  cancelado: "Cancelado",
};

function formatarValor(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface ProtocoloGerenciarLinhaProps {
  protocolo: Protocolo;
  nomeCliente: string;
  onAtualizado: () => void;
}

export function ProtocoloGerenciarLinha({
  protocolo,
  nomeCliente,
  onAtualizado,
}: ProtocoloGerenciarLinhaProps) {
  const { token } = useAuth();
  const [valorOrcamento, setValorOrcamento] = useState(protocolo.valor_orcamento ?? "");
  const [erro, setErro] = useState<string | null>(null);
  const [processando, setProcessando] = useState(false);

  async function executar(acao: () => Promise<Protocolo>) {
    if (!token) {
      setErro("Faça login novamente.");
      return;
    }
    setProcessando(true);
    setErro(null);
    try {
      await acao();
      onAtualizado();
    } catch (erroCapturado) {
      setErro(
        erroCapturado instanceof Error ? erroCapturado.message : "Erro ao atualizar protocolo.",
      );
    } finally {
      setProcessando(false);
    }
  }

  function handleDefinirOrcamento() {
    executar(() =>
      atualizarProtocolo(
        protocolo.id,
        {
          veiculo: protocolo.veiculo,
          categoria: protocolo.categoria,
          descricao: protocolo.descricao,
          mecanico_id: protocolo.mecanico_id,
          valor_orcamento: valorOrcamento,
        },
        token as string,
      ),
    );
  }

  function handleCancelar() {
    const motivo = window.prompt("Motivo do cancelamento (opcional):") ?? undefined;
    executar(() => cancelarProtocolo(protocolo.id, token as string, motivo));
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:flex-row sm:items-center">
      <div className="flex-1">
        <ProtocoloCard protocolo={protocolo} />
        <p className="mt-1 text-sm text-gray-500">
          {nomeCliente} · {STATUS_LABELS[protocolo.status]}
        </p>
        {protocolo.descricao && <p className="text-sm text-gray-500">{protocolo.descricao}</p>}
        {protocolo.motivo_cancelamento && (
          <p className="text-sm text-gray-500">
            Motivo do cancelamento: {protocolo.motivo_cancelamento}
          </p>
        )}
        {erro && <p className="text-sm text-red-700">{erro}</p>}
      </div>

      {protocolo.status === "aguardando_aprovacao" && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <input
            value={valorOrcamento}
            onChange={(evento) => setValorOrcamento(evento.target.value)}
            placeholder="Valor do orçamento"
            inputMode="decimal"
            className="w-32 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1a2332] focus:outline-none"
          />
          <button
            type="button"
            disabled={processando || !valorOrcamento}
            onClick={handleDefinirOrcamento}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
          >
            Definir orçamento
          </button>
          <button
            type="button"
            disabled={processando || !protocolo.valor_orcamento}
            onClick={() => executar(() => aprovarProtocolo(protocolo.id, token as string))}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
          >
            Aprovar
          </button>
          <button
            type="button"
            disabled={processando}
            onClick={handleCancelar}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
          >
            Cancelar
          </button>
        </div>
      )}

      {protocolo.status === "em_execucao" && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {protocolo.valor_orcamento && (
            <span className="text-sm text-gray-600">
              {formatarValor(protocolo.valor_orcamento)}
            </span>
          )}
          <button
            type="button"
            disabled={processando}
            onClick={() => executar(() => concluirProtocolo(protocolo.id, token as string))}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
          >
            Concluir
          </button>
          <button
            type="button"
            disabled={processando}
            onClick={handleCancelar}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
          >
            Cancelar
          </button>
        </div>
      )}

      {(protocolo.status === "pronto" || protocolo.status === "cancelado") &&
        protocolo.valor_orcamento && (
          <span className="shrink-0 text-sm text-gray-600">
            {formatarValor(protocolo.valor_orcamento)}
          </span>
        )}
    </div>
  );
}
