import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { criarCliente } from "../services/clienteService";
import type { ClienteCreateInput } from "../types/cliente";
import { CamposCliente } from "./CamposCliente";

const CAMPOS_VAZIOS: ClienteCreateInput = { nome: "", telefone: "", email: "", endereco: "" };

interface ClienteFormularioProps {
  onCriado: () => void;
}

export function ClienteFormulario({ onCriado }: ClienteFormularioProps) {
  const { token } = useAuth();
  const [novoCliente, setNovoCliente] = useState<ClienteCreateInput>(CAMPOS_VAZIOS);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);

    if (!token) {
      setErro("Faça login novamente para cadastrar clientes.");
      return;
    }

    setEnviando(true);
    try {
      await criarCliente(novoCliente, token);
      setNovoCliente(CAMPOS_VAZIOS);
      onCriado();
    } catch (erroCapturado) {
      setErro(
        erroCapturado instanceof Error ? erroCapturado.message : "Erro ao cadastrar cliente.",
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-8 grid grid-cols-1 gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:grid-cols-3"
    >
      <CamposCliente valores={novoCliente} aoMudar={setNovoCliente} />

      {erro && <p className="col-span-full text-sm text-red-700">{erro}</p>}

      <button
        type="submit"
        disabled={enviando}
        className="col-span-full w-fit rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
      >
        {enviando ? "Cadastrando..." : "Cadastrar cliente"}
      </button>
    </form>
  );
}
