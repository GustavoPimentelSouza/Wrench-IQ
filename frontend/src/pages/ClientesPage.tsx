import { useEffect, useState, type FormEvent } from "react";
import { ProtocoloCard } from "../components/ProtocoloCard";
import { useAuth } from "../context/AuthContext";
import {
  atualizarCliente,
  criarCliente,
  excluirCliente,
  listarClientes,
} from "../services/clienteService";
import { listarProtocolosDoCliente } from "../services/protocoloService";
import type { Cliente, ClienteCreateInput } from "../types/cliente";
import type { Protocolo } from "../types/protocolo";

const CAMPOS_VAZIOS: ClienteCreateInput = { nome: "", telefone: "", email: "" };

function paraFormulario(cliente: Cliente): ClienteCreateInput {
  return { nome: cliente.nome, telefone: cliente.telefone, email: cliente.email ?? "" };
}

interface CamposClienteProps {
  valores: ClienteCreateInput;
  aoMudar: (valores: ClienteCreateInput) => void;
}

function CamposCliente({ valores, aoMudar }: CamposClienteProps) {
  return (
    <>
      <input
        value={valores.nome}
        onChange={(evento) => aoMudar({ ...valores, nome: evento.target.value })}
        placeholder="Nome"
        required
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
      <input
        value={valores.telefone}
        onChange={(evento) => aoMudar({ ...valores, telefone: evento.target.value })}
        placeholder="Telefone com DDI, só números (ex: 5511999999999)"
        pattern="\d{10,15}"
        maxLength={15}
        required
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
      <input
        value={valores.email ?? ""}
        onChange={(evento) => aoMudar({ ...valores, email: evento.target.value })}
        placeholder="E-mail (opcional)"
        type="email"
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
    </>
  );
}

export function ClientesPage() {
  const { token } = useAuth();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const [novoCliente, setNovoCliente] = useState<ClienteCreateInput>(CAMPOS_VAZIOS);
  const [erroFormulario, setErroFormulario] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [clienteEmEdicao, setClienteEmEdicao] = useState<ClienteCreateInput>(CAMPOS_VAZIOS);
  const [erroEdicao, setErroEdicao] = useState<string | null>(null);
  const [salvandoEdicao, setSalvandoEdicao] = useState(false);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);

  const [historicoAbertoId, setHistoricoAbertoId] = useState<string | null>(null);
  const [protocolosDoHistorico, setProtocolosDoHistorico] = useState<Protocolo[]>([]);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);

  function carregarClientes() {
    setCarregando(true);
    listarClientes()
      .then(setClientes)
      .catch(() => setErro("Não foi possível carregar os clientes."))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregarClientes();
  }, []);

  async function handleCriar(evento: FormEvent) {
    evento.preventDefault();
    setErroFormulario(null);

    if (!token) {
      setErroFormulario("Faça login novamente para cadastrar clientes.");
      return;
    }

    setEnviando(true);
    try {
      await criarCliente(novoCliente, token);
      setNovoCliente(CAMPOS_VAZIOS);
      carregarClientes();
    } catch (erroCapturado) {
      setErroFormulario(
        erroCapturado instanceof Error ? erroCapturado.message : "Erro ao cadastrar cliente.",
      );
    } finally {
      setEnviando(false);
    }
  }

  function iniciarEdicao(cliente: Cliente) {
    setEditandoId(cliente.id);
    setClienteEmEdicao(paraFormulario(cliente));
    setErroEdicao(null);
  }

  function cancelarEdicao() {
    setEditandoId(null);
    setErroEdicao(null);
  }

  async function salvarEdicao(evento: FormEvent) {
    evento.preventDefault();
    if (!editandoId) return;

    if (!token) {
      setErroEdicao("Faça login novamente para editar clientes.");
      return;
    }

    setSalvandoEdicao(true);
    setErroEdicao(null);
    try {
      await atualizarCliente(editandoId, clienteEmEdicao, token);
      setEditandoId(null);
      carregarClientes();
    } catch (erroCapturado) {
      setErroEdicao(
        erroCapturado instanceof Error ? erroCapturado.message : "Erro ao atualizar cliente.",
      );
    } finally {
      setSalvandoEdicao(false);
    }
  }

  async function handleExcluir(cliente: Cliente) {
    if (!token) {
      setErro("Faça login novamente para excluir clientes.");
      return;
    }

    const confirmado = window.confirm(
      `Excluir o cliente "${cliente.nome}"? Essa ação não pode ser desfeita.`,
    );
    if (!confirmado) return;

    setExcluindoId(cliente.id);
    try {
      await excluirCliente(cliente.id, token);
      carregarClientes();
    } catch (erroCapturado) {
      setErro(
        erroCapturado instanceof Error ? erroCapturado.message : "Erro ao excluir cliente.",
      );
    } finally {
      setExcluindoId(null);
    }
  }

  async function alternarHistorico(cliente: Cliente) {
    if (historicoAbertoId === cliente.id) {
      setHistoricoAbertoId(null);
      return;
    }

    setHistoricoAbertoId(cliente.id);
    setCarregandoHistorico(true);
    try {
      const protocolos = await listarProtocolosDoCliente(cliente.id);
      setProtocolosDoHistorico(protocolos);
    } catch {
      setProtocolosDoHistorico([]);
    } finally {
      setCarregandoHistorico(false);
    }
  }

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Clientes</h2>

      <form
        onSubmit={handleCriar}
        className="mb-8 grid grid-cols-1 gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:grid-cols-3"
      >
        <CamposCliente valores={novoCliente} aoMudar={setNovoCliente} />

        {erroFormulario && (
          <p className="col-span-full text-sm text-red-700">{erroFormulario}</p>
        )}

        <button
          type="submit"
          disabled={enviando}
          className="col-span-full w-fit rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
        >
          {enviando ? "Cadastrando..." : "Cadastrar cliente"}
        </button>
      </form>

      {erro && <p className="mb-4 text-sm text-red-700">{erro}</p>}
      {carregando && !erro && <p className="text-sm text-gray-500">Carregando...</p>}

      {!carregando && !erro && clientes.length === 0 && (
        <p className="text-sm text-gray-500">Nenhum cliente cadastrado ainda.</p>
      )}

      {!carregando && !erro && clientes.length > 0 && (
        <div className="flex flex-col gap-3">
          {clientes.map((cliente) =>
            editandoId === cliente.id ? (
              <form
                key={cliente.id}
                onSubmit={salvarEdicao}
                className="grid grid-cols-1 gap-3 rounded-xl border border-[#1a2332] bg-white p-4 shadow-sm sm:grid-cols-3"
              >
                <CamposCliente valores={clienteEmEdicao} aoMudar={setClienteEmEdicao} />

                {erroEdicao && (
                  <p className="col-span-full text-sm text-red-700">{erroEdicao}</p>
                )}

                <div className="col-span-full flex gap-2">
                  <button
                    type="submit"
                    disabled={salvandoEdicao}
                    className="rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
                  >
                    {salvandoEdicao ? "Salvando..." : "Salvar"}
                  </button>
                  <button
                    type="button"
                    onClick={cancelarEdicao}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            ) : (
              <div key={cliente.id} className="rounded-xl border border-gray-100 bg-white shadow-sm">
                <div className="flex items-center gap-4 p-4">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{cliente.nome}</p>
                    <p className="text-sm text-gray-500">
                      {cliente.telefone} {cliente.email ? `· ${cliente.email}` : ""}
                    </p>
                  </div>

                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      onClick={() => alternarHistorico(cliente)}
                      className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                    >
                      {historicoAbertoId === cliente.id ? "Fechar histórico" : "Ver histórico"}
                    </button>
                    <button
                      type="button"
                      onClick={() => iniciarEdicao(cliente)}
                      className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      onClick={() => handleExcluir(cliente)}
                      disabled={excluindoId === cliente.id}
                      className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
                    >
                      {excluindoId === cliente.id ? "Excluindo..." : "Excluir"}
                    </button>
                  </div>
                </div>

                {historicoAbertoId === cliente.id && (
                  <div className="border-t border-gray-100 bg-gray-50 p-4">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Histórico de serviços
                    </p>
                    {carregandoHistorico && (
                      <p className="text-sm text-gray-500">Carregando...</p>
                    )}
                    {!carregandoHistorico && protocolosDoHistorico.length === 0 && (
                      <p className="text-sm text-gray-500">
                        Nenhum protocolo registrado para este cliente ainda.
                      </p>
                    )}
                    {!carregandoHistorico && protocolosDoHistorico.length > 0 && (
                      <div className="flex flex-col gap-2">
                        {protocolosDoHistorico.map((protocolo) => (
                          <ProtocoloCard key={protocolo.id} protocolo={protocolo} />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}
