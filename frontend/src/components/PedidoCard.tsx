import type { Pedido, StatusPedido } from "../types/pedido";

const STATUS_LABELS: Record<StatusPedido, string> = {
  aguardando_pagamento: "Aguardando pagamento",
  aguardando_retirada: "Aguardando retirada",
  aguardando_conferencia: "Aguardando conferência",
  despachado: "Despachado",
  entregue: "Entregue",
  cancelado: "Cancelado",
};

const STATUS_CORES: Record<StatusPedido, string> = {
  aguardando_pagamento: "bg-amber-100 text-amber-800",
  aguardando_retirada: "bg-sky-100 text-sky-700",
  aguardando_conferencia: "bg-violet-100 text-violet-700",
  despachado: "bg-blue-100 text-blue-700",
  entregue: "bg-emerald-100 text-emerald-700",
  cancelado: "bg-gray-200 text-gray-600",
};

function formatarValor(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface PedidoCardProps {
  pedido: Pedido;
  nomeCliente: string;
  nomePeca: string;
  processando: boolean;
  onConfirmarPagamento: () => void;
  onConfirmarConferencia: () => void;
  onMarcarEntregue: () => void;
  onCancelar: () => void;
}

export function PedidoCard({
  pedido,
  nomeCliente,
  nomePeca,
  processando,
  onConfirmarPagamento,
  onConfirmarConferencia,
  onMarcarEntregue,
  onCancelar,
}: PedidoCardProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      <div className="flex-1">
        <p className="font-medium text-gray-900">
          #{String(pedido.numero).padStart(4, "0")} · {nomeCliente}
        </p>
        <p className="text-sm text-gray-500">
          {pedido.quantidade}x {nomePeca} · {formatarValor(pedido.valor_total)} ·{" "}
          {pedido.tipo_entrega === "envio_remoto" ? "Envio remoto" : "Retirada local"}
        </p>
        {pedido.link_pagamento && (
          <a
            href={pedido.link_pagamento}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-sky-700 underline"
          >
            Link de pagamento
          </a>
        )}
        {pedido.dentro_do_prazo_arrependimento && (
          <p className="text-xs text-amber-700">
            Dentro do prazo de arrependimento (7 dias)
          </p>
        )}
      </div>

      <span
        className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_CORES[pedido.status]}`}
      >
        {STATUS_LABELS[pedido.status]}
      </span>

      <div className="flex shrink-0 gap-2">
        {pedido.status === "aguardando_pagamento" && (
          <button
            type="button"
            disabled={processando}
            onClick={onConfirmarPagamento}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
          >
            Confirmar pagamento
          </button>
        )}
        {pedido.status === "aguardando_conferencia" && (
          <button
            type="button"
            disabled={processando}
            onClick={onConfirmarConferencia}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
          >
            Confirmar conferência
          </button>
        )}
        {(pedido.status === "despachado" || pedido.status === "aguardando_retirada") && (
          <button
            type="button"
            disabled={processando}
            onClick={onMarcarEntregue}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
          >
            Marcar entregue
          </button>
        )}
        {pedido.status !== "entregue" && pedido.status !== "cancelado" && (
          <button
            type="button"
            disabled={processando}
            onClick={onCancelar}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
          >
            Cancelar
          </button>
        )}
      </div>
    </div>
  );
}

export { STATUS_LABELS };
