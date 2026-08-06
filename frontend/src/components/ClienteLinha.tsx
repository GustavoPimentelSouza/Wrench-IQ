import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { atualizarCliente, excluirCliente } from "../services/clienteService";
import { listarPedidosDoCliente } from "../services/pedidoService";
import { listarProtocolosDoCliente } from "../services/protocoloService";
import type { Cliente, ClienteCreateInput } from "../types/cliente";
import type { Pedido } from "../types/pedido";
import type { Protocolo } from "../types/protocolo";
import { CamposCliente } from "./CamposCliente";
import { ProtocoloCard } from "./ProtocoloCard";

function paraFormulario(cliente: Cliente): ClienteCreateInput {
  return {
    // Sem isso, editar um cliente sem nome pré-preenchia o campo com o
    // telefone (o valor cru salvo) — obrigando apagar antes de digitar o
    // nome de verdade. Começa vazio pra digitar direto.
    nome: cliente.nome === cliente.telefone ? "" : cliente.nome,
    telefone: cliente.telefone,
    email: cliente.email ?? "",
    endereco: cliente.endereco ?? "",
  };
}

// "Cadastro incompleto" = nome ainda é só o telefone (cliente novo via
// WhatsApp nunca deu o nome) ou não tem endereço — os dois dados que
// tornam o atendimento mais profissional (ver discussão do dia a dia).
function cadastroIncompleto(cliente: Cliente): boolean {
  return cliente.nome === cliente.telefone || !cliente.endereco;
}

// Mostrar o telefone cru como se fosse o nome (nome === telefone é só o
// valor padrão de cliente novo via WhatsApp) confundia — parecia erro,
// repetindo o mesmo número duas vezes na linha. Isso deixa claro que
// "ainda não tem nome" é um estado, não um dado de verdade.
function nomeParaExibir(cliente: Cliente): string {
  return cliente.nome === cliente.telefone ? "Cliente sem nome" : cliente.nome;
}

function formatarValor(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// Total gasto = soma do que já foi de fato comprometido com a gente,
// protocolo (serviço) + pedido (peça) — cancelado não conta, porque nunca
// virou receita de verdade.
function calcularTotalGasto(protocolos: Protocolo[], pedidos: Pedido[]): number {
  const totalProtocolos = protocolos
    .filter((p) => p.status !== "cancelado" && p.valor_orcamento)
    .reduce((soma, p) => soma + Number(p.valor_orcamento), 0);
  const totalPedidos = pedidos
    .filter((p) => p.status !== "cancelado")
    .reduce((soma, p) => soma + Number(p.valor_total), 0);
  return totalProtocolos + totalPedidos;
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
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
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
      const [protocolosCarregados, pedidosCarregados] = await Promise.all([
        listarProtocolosDoCliente(cliente.id),
        token ? listarPedidosDoCliente(cliente.id, token) : Promise.resolve([]),
      ]);
      setProtocolos(protocolosCarregados);
      setPedidos(pedidosCarregados);
    } catch {
      setProtocolos([]);
      setPedidos([]);
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
          <div className="flex items-center gap-2">
            <p
              className={
                cliente.nome === cliente.telefone
                  ? "italic text-gray-400"
                  : "font-medium text-gray-900"
              }
            >
              {nomeParaExibir(cliente)}
            </p>
            {cadastroIncompleto(cliente) && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                Dados incompletos
              </span>
            )}
          </div>
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
          {!carregandoHistorico && (protocolos.length > 0 || pedidos.length > 0) && (
            <p className="mb-3 text-sm font-medium text-gray-900">
              Total gasto: {formatarValor(calcularTotalGasto(protocolos, pedidos))}
            </p>
          )}

          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
            Serviços (protocolos)
          </p>
          {carregandoHistorico && <p className="text-sm text-gray-500">Carregando...</p>}
          {!carregandoHistorico && protocolos.length === 0 && (
            <p className="mb-4 text-sm text-gray-500">Nenhum protocolo ainda.</p>
          )}
          {!carregandoHistorico && protocolos.length > 0 && (
            <div className="mb-4 flex flex-col gap-2">
              {protocolos.map((protocolo) => (
                <ProtocoloCard key={protocolo.id} protocolo={protocolo} />
              ))}
            </div>
          )}

          {/* Peças compradas — antes só aparecia em Pedidos, sem ligação
              nenhuma com o cadastro do cliente; sem isso o histórico
              ficava incompleto (só metade do que o cliente já consumiu). */}
          {!carregandoHistorico && (
            <>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Peças (pedidos)
              </p>
              {pedidos.length === 0 && (
                <p className="text-sm text-gray-500">Nenhum pedido ainda.</p>
              )}
              {pedidos.length > 0 && (
                <div className="flex flex-col gap-2">
                  {pedidos.map((pedido) => (
                    <div
                      key={pedido.id}
                      className="rounded-xl border border-gray-100 bg-white p-3 text-sm"
                    >
                      #{String(pedido.numero).padStart(4, "0")} · {pedido.quantidade}x ·{" "}
                      {formatarValor(Number(pedido.valor_total))} · {pedido.status}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
