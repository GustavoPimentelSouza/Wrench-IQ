import { useEffect, useState } from "react";
import { PedidoCard, STATUS_LABELS } from "../components/PedidoCard";
import { PedidoFormulario } from "../components/PedidoFormulario";
import { useAuth } from "../context/AuthContext";
import { listarClientes } from "../services/clienteService";
import { listarPecas } from "../services/pecaService";
import {
  cancelarPedido,
  confirmarConferencia,
  confirmarPagamento,
  expirarRetiradas,
  listarPedidos,
  marcarEntregue,
} from "../services/pedidoService";
import type { Cliente } from "../types/cliente";
import type { Peca } from "../types/peca";
import type { Pedido, StatusPedido } from "../types/pedido";

export function PedidosPage() {
  const { token } = useAuth();
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [pecas, setPecas] = useState<Peca[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [processandoId, setProcessandoId] = useState<string | null>(null);
  const [filtroStatus, setFiltroStatus] = useState<StatusPedido | "">("");

  function carregarTudo() {
    if (!token) return;
    setCarregando(true);
    // expirarRetiradas roda primeiro, "de graça", toda vez que a tela abre —
    // é a limpeza preguiçosa de reserva de retirada local vencida (ver
    // application/pedido_use_cases.py:cancelar_expirados). Se falhar, não
    // trava o carregamento normal da lista.
    expirarRetiradas(token)
      .catch(() => undefined)
      .finally(() => {
        Promise.all([
          listarPedidos(token, filtroStatus || undefined),
          listarClientes(),
          listarPecas(),
        ])
          .then(([pedidosCarregados, clientesCarregados, pecasCarregadas]) => {
            setPedidos(pedidosCarregados);
            setClientes(clientesCarregados);
            setPecas(pecasCarregadas);
          })
          .catch(() => setErro("Não foi possível carregar os pedidos."))
          .finally(() => setCarregando(false));
      });
  }

  useEffect(() => {
    carregarTudo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, filtroStatus]);

  function nomeCliente(clienteId: string): string {
    return clientes.find((c) => c.id === clienteId)?.nome ?? clienteId;
  }

  function nomePeca(pecaId: string): string {
    return pecas.find((p) => p.id === pecaId)?.nome ?? pecaId;
  }

  async function executarAcao(acao: (id: string, token: string) => Promise<Pedido>, pedido: Pedido) {
    if (!token) {
      setErro("Faça login novamente.");
      return;
    }
    setProcessandoId(pedido.id);
    try {
      await acao(pedido.id, token);
      carregarTudo();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao atualizar pedido.");
    } finally {
      setProcessandoId(null);
    }
  }

  function handleCancelar(pedido: Pedido) {
    const confirmado = window.confirm(`Cancelar o pedido #${pedido.numero}?`);
    if (!confirmado) return;
    executarAcao(cancelarPedido, pedido);
  }

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Pedidos</h2>

      <PedidoFormulario clientes={clientes} pecas={pecas} onCriado={carregarTudo} />

      <div className="mb-4 flex items-center gap-2">
        <label htmlFor="filtro-status" className="text-sm text-gray-600">
          Status:
        </label>
        <select
          id="filtro-status"
          value={filtroStatus}
          onChange={(evento) => setFiltroStatus(evento.target.value as StatusPedido | "")}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1a2332] focus:outline-none"
        >
          <option value="">Todos</option>
          {(Object.keys(STATUS_LABELS) as StatusPedido[]).map((status) => (
            <option key={status} value={status}>
              {STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </div>

      {erro && <p className="mb-4 text-sm text-red-700">{erro}</p>}
      {carregando && !erro && <p className="text-sm text-gray-500">Carregando...</p>}

      {!carregando && !erro && pedidos.length === 0 && (
        <p className="text-sm text-gray-500">
          {filtroStatus ? "Nenhum pedido com esse status." : "Nenhum pedido criado ainda."}
        </p>
      )}

      {!carregando && !erro && pedidos.length > 0 && (
        <div className="flex flex-col gap-3">
          {pedidos.map((pedido) => (
            <PedidoCard
              key={pedido.id}
              pedido={pedido}
              nomeCliente={nomeCliente(pedido.cliente_id)}
              nomePeca={nomePeca(pedido.peca_id)}
              processando={processandoId === pedido.id}
              onConfirmarPagamento={() => executarAcao(confirmarPagamento, pedido)}
              onConfirmarConferencia={() => executarAcao(confirmarConferencia, pedido)}
              onMarcarEntregue={() => executarAcao(marcarEntregue, pedido)}
              onCancelar={() => handleCancelar(pedido)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
