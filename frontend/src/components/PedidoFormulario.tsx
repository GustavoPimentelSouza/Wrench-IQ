import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { criarPedido } from "../services/pedidoService";
import type { Cliente } from "../types/cliente";
import type { Peca } from "../types/peca";
import type { TipoEntrega } from "../types/pedido";

function formatarValor(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface PedidoFormularioProps {
  clientes: Cliente[];
  pecas: Peca[];
  onCriado: () => void;
}

export function PedidoFormulario({ clientes, pecas, onCriado }: PedidoFormularioProps) {
  const { token } = useAuth();
  const [clienteId, setClienteId] = useState("");
  const [pecaId, setPecaId] = useState("");
  const [quantidade, setQuantidade] = useState("1");
  const [tipoEntrega, setTipoEntrega] = useState<TipoEntrega>("retirada_local");
  const [enderecoEntrega, setEnderecoEntrega] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);

    if (!token) {
      setErro("Faça login novamente para criar pedidos.");
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
      onCriado();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao criar pedido.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
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

      {erro && <p className="col-span-full text-sm text-red-700">{erro}</p>}

      <button
        type="submit"
        disabled={enviando}
        className="col-span-full w-fit rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
      >
        {enviando ? "Criando..." : "Criar pedido"}
      </button>
    </form>
  );
}
