import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { atualizarCliente, excluirCliente } from "../services/clienteService";
import { listarProtocolosDoCliente } from "../services/protocoloService";
import type { Cliente, ClienteCreateInput } from "../types/cliente";
import type { Protocolo } from "../types/protocolo";
import { CamposCliente } from "./CamposCliente";
import { ProtocoloCard } from "./ProtocoloCard";

function paraFormulario(cliente: Cliente): ClienteCreateInput {
  return { nome: cliente.nome, telefone: cliente.telefone, email: cliente.email ?? "" };
}

interface ClienteLinhaProps {
  cliente: Cliente;
  onAtualizado: () => void;
}

export function ClienteLinha({ cliente, onAtualizado }: ClienteLinhaProps) {
  const { token } = useAuth();
  const [editando, setEditando] = useState(false);
  const [valores, setValores] = useState<ClienteCreateInput>(() => paraFormulario(cliente));
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [excluindo, setExcluindo] = useState(false);

  const [historicoAberto, setHistoricoAberto] = useState(false);
  const [protocolos, setProtocolos] = useState<Protocolo[]>([]);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);

  function iniciarEdicao() {
    setValores(paraFormulario(cliente));
    setErro(null);
    setEditando(true);
  }

  async function handleSalvar(evento: FormEvent) {
    evento.preventDefault();
    if (!token) {
      setErro("Faça login novamente para editar clientes.");
      return;
    }

    setSalvando(true);
    setErro(null);
    try {
      await atualizarCliente(cliente.id, valores, token);
      setEditando(false);
      onAtualizado();
    } catch (erroCapturado) {
      setErro(
        erroCapturado instanceof Error ? erroCapturado.message : "Erro ao atualizar cliente.",
      );
    } finally {
      setSalvando(false);
    }
  }

  async function handleExcluir() {
    if (!token) {
      setErro("Faça login novamente para excluir clientes.");
      return;
    }
    const confirmado = window.confirm(
      `Excluir o cliente "${cliente.nome}"? Essa ação não pode ser desfeita.`,
    );
    if (!confirmado) return;

    setExcluindo(true);
    try {
      await excluirCliente(cliente.id, token);
      onAtualizado();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao excluir cliente.");
    } finally {
      setExcluindo(false);
    }
  }

  async function alternarHistorico() {
    if (historicoAberto) {
      setHistoricoAberto(false);
      return;
    }
    setHistoricoAberto(true);
    setCarregandoHistorico(true);
    try {
      setProtocolos(await listarProtocolosDoCliente(cliente.id));
    } catch {
      setProtocolos([]);
    } finally {
      setCarregandoHistorico(false);
    }
  }

  if (editando) {
    return (
      <form
        onSubmit={handleSalvar}
        className="grid grid-cols-1 gap-3 rounded-xl border border-[#1a2332] bg-white p-4 shadow-sm sm:grid-cols-3"
      >
        <CamposCliente valores={valores} aoMudar={setValores} />

        {erro && <p className="col-span-full text-sm text-red-700">{erro}</p>}

        <div className="col-span-full flex gap-2">
          <button
            type="submit"
            disabled={salvando}
            className="rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Salvar"}
          </button>
          <button
            type="button"
            onClick={() => setEditando(false)}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
          >
            Cancelar
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
      <div className="flex items-center gap-4 p-4">
        <div className="flex-1">
          <p className="font-medium text-gray-900">{cliente.nome}</p>
          <p className="text-sm text-gray-500">
            {cliente.telefone} {cliente.email ? `· ${cliente.email}` : ""}
          </p>
          {erro && <p className="text-sm text-red-700">{erro}</p>}
        </div>

        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={alternarHistorico}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
          >
            {historicoAberto ? "Fechar histórico" : "Ver histórico"}
          </button>
          <button
            type="button"
            onClick={iniciarEdicao}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={handleExcluir}
            disabled={excluindo}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
          >
            {excluindo ? "Excluindo..." : "Excluir"}
          </button>
        </div>
      </div>

      {historicoAberto && (
        <div className="border-t border-gray-100 bg-gray-50 p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
            Histórico de serviços
          </p>
          {carregandoHistorico && <p className="text-sm text-gray-500">Carregando...</p>}
          {!carregandoHistorico && protocolos.length === 0 && (
            <p className="text-sm text-gray-500">
              Nenhum protocolo registrado para este cliente ainda.
            </p>
          )}
          {!carregandoHistorico && protocolos.length > 0 && (
            <div className="flex flex-col gap-2">
              {protocolos.map((protocolo) => (
                <ProtocoloCard key={protocolo.id} protocolo={protocolo} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
