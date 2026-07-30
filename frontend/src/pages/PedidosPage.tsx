import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { listarClientes } from "../services/clienteService";
import { listarPecas } from "../services/pecaService";
import {
  cancelarPedido,
  confirmarConferencia,
  confirmarPagamento,
  criarPedido,
  listarPedidos,
  marcarEntregue,
} from "../services/pedidoService";
import type { Cliente } from "../types/cliente";
import type { Peca } from "../types/peca";
import type { Pedido, StatusPedido, TipoEntrega } from "../types/pedido";

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

export function PedidosPage() {
  const { token } = useAuth();
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [pecas, setPecas] = useState<Peca[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const [clienteId, setClienteId] = useState("");
  const [pecaId, setPecaId] = useState("");
  const [quantidade, setQuantidade] = useState("1");
  const [tipoEntrega, setTipoEntrega] = useState<TipoEntrega>("retirada_local");
  const [enderecoEntrega, setEnderecoEntrega] = useState("");
  const [erroFormulario, setErroFormulario] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const [processandoId, setProcessandoId] = useState<string | null>(null);
  const [filtroStatus, setFiltroStatus] = useState<StatusPedido | "">("");

  function carregarTudo() {
    if (!token) return;
    setCarregando(true);
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

  async function handleCriar(evento: FormEvent) {
    evento.preventDefault();
    setErroFormulario(null);

    if (!token) {
      setErroFormulario("Faça login novamente para criar pedidos.");
      return;
    }

    setEnviando(true);
    try {
      await criarPedido(
        {
          cliente_id: clienteId,
          peca_id: pecaId,
          quantidade: Number(quantidade),
          tipo_entrega: tipoEntrega,
          endereco_entrega: tipoEntrega === "envio_remoto" ? enderecoEntrega : undefined,
        },
        token,
      );
      setClienteId("");
      setPecaId("");
      setQuantidade("1");
      setTipoEntrega("retirada_local");
      setEnderecoEntrega("");
      carregarTudo();
    } catch (erroCapturado) {
      setErroFormulario(
        erroCapturado instanceof Error ? erroCapturado.message : "Erro ao criar pedido.",
      );
    } finally {
      setEnviando(false);
    }
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

      <form
        onSubmit={handleCriar}
        className="mb-8 grid grid-cols-1 gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-5"
      >
        <select
          value={clienteId}
          onChange={(evento) => setClienteId(evento.target.value)}
          required
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
        >
          <option value="">Cliente...</option>
          {clientes.map((cliente) => (
            <option key={cliente.id} value={cliente.id}>
              {cliente.nome}
            </option>
          ))}
        </select>

        <select
          value={pecaId}
          onChange={(evento) => setPecaId(evento.target.value)}
          required
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
        >
          <option value="">Peça...</option>
          {pecas.map((peca) => (
            <option key={peca.id} value={peca.id}>
              {peca.nome} ({formatarValor(peca.preco)})
            </option>
          ))}
        </select>

        <input
          value={quantidade}
          onChange={(evento) => setQuantidade(evento.target.value)}
          type="number"
          min={1}
          required
          placeholder="Quantidade"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
        />

        <select
          value={tipoEntrega}
          onChange={(evento) => setTipoEntrega(evento.target.value as TipoEntrega)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
        >
          <option value="retirada_local">Retirada local</option>
          <option value="envio_remoto">Envio remoto</option>
        </select>

        {tipoEntrega === "envio_remoto" && (
          <input
            value={enderecoEntrega}
            onChange={(evento) => setEnderecoEntrega(evento.target.value)}
            placeholder="Endereço de entrega"
            required
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
          />
        )}

        {erroFormulario && (
          <p className="col-span-full text-sm text-red-700">{erroFormulario}</p>
        )}

        <button
          type="submit"
          disabled={enviando}
          className="col-span-full w-fit rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
        >
          {enviando ? "Criando..." : "Criar pedido"}
        </button>
      </form>

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
          {filtroStatus
            ? "Nenhum pedido com esse status."
            : "Nenhum pedido criado ainda."}
        </p>
      )}

      {!carregando && !erro && pedidos.length > 0 && (
        <div className="flex flex-col gap-3">
          {pedidos.map((pedido) => (
            <div
              key={pedido.id}
              className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-100 bg-white p-4 shadow-sm"
            >
              <div className="flex-1">
                <p className="font-medium text-gray-900">
                  #{String(pedido.numero).padStart(4, "0")} · {nomeCliente(pedido.cliente_id)}
                </p>
                <p className="text-sm text-gray-500">
                  {pedido.quantidade}x {nomePeca(pedido.peca_id)} ·{" "}
                  {formatarValor(pedido.valor_total)} ·{" "}
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
                    disabled={processandoId === pedido.id}
                    onClick={() => executarAcao(confirmarPagamento, pedido)}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
                  >
                    Confirmar pagamento
                  </button>
                )}
                {pedido.status === "aguardando_conferencia" && (
                  <button
                    type="button"
                    disabled={processandoId === pedido.id}
                    onClick={() => executarAcao(confirmarConferencia, pedido)}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
                  >
                    Confirmar conferência
                  </button>
                )}
                {(pedido.status === "despachado" || pedido.status === "aguardando_retirada") && (
                  <button
                    type="button"
                    disabled={processandoId === pedido.id}
                    onClick={() => executarAcao(marcarEntregue, pedido)}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
                  >
                    Marcar entregue
                  </button>
                )}
                {pedido.status !== "entregue" && pedido.status !== "cancelado" && (
                  <button
                    type="button"
                    disabled={processandoId === pedido.id}
                    onClick={() => handleCancelar(pedido)}
                    className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
                  >
                    Cancelar
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
