import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { criarProtocolo } from "../services/protocoloService";
import type { Cliente } from "../types/cliente";

interface ProtocoloFormularioProps {
  clientes: Cliente[];
  onCriado: () => void;
}

export function ProtocoloFormulario({ clientes, onCriado }: ProtocoloFormularioProps) {
  const { token } = useAuth();
  const [clienteId, setClienteId] = useState("");
  const [veiculo, setVeiculo] = useState("");
  const [categoria, setCategoria] = useState("");
  const [descricao, setDescricao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);

    if (!token) {
      setErro("Faça login novamente para criar protocolos.");
      return;
    }

    setEnviando(true);
    try {
      await criarProtocolo(
        { cliente_id: clienteId, veiculo, categoria, descricao: descricao || undefined },
        token,
      );
      setClienteId("");
      setVeiculo("");
      setCategoria("");
      setDescricao("");
      onCriado();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao criar protocolo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-8 grid grid-cols-1 gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4"
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

      <input
        value={veiculo}
        onChange={(evento) => setVeiculo(evento.target.value)}
        placeholder="Veículo (ex: Onix 2022)"
        required
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />

      <input
        value={categoria}
        onChange={(evento) => setCategoria(evento.target.value)}
        placeholder="Categoria (ex: farol, pintura)"
        required
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />

      <input
        value={descricao}
        onChange={(evento) => setDescricao(evento.target.value)}
        placeholder="Descrição (opcional)"
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />

      {erro && <p className="col-span-full text-sm text-red-700">{erro}</p>}

      <button
        type="submit"
        disabled={enviando}
        className="col-span-full w-fit rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
      >
        {enviando ? "Criando..." : "Criar protocolo"}
      </button>
    </form>
  );
}
