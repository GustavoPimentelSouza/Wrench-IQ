import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { atualizarStatusAgendamento, listarAgendamentos } from "../services/agendamentoService";
import { listarClientes } from "../services/clienteService";
import type { Agendamento, StatusAgendamento } from "../types/agendamento";
import type { Cliente } from "../types/cliente";

const ROTULOS_STATUS: Record<StatusAgendamento, string> = {
  agendado: "Agendado",
  confirmado: "Confirmado",
  concluido: "Concluído",
  cancelado: "Cancelado",
};

function formatarDataHora(dataHora: string): string {
  return new Date(dataHora).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AgendaPage() {
  const { token } = useAuth();
  const [agendamentos, setAgendamentos] = useState<Agendamento[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [atualizandoId, setAtualizandoId] = useState<string | null>(null);

  function carregarTudo() {
    setCarregando(true);
    Promise.all([listarAgendamentos(), listarClientes()])
      .then(([lista, clientesCarregados]) => {
        // Mais próximo primeiro — é a mesma lógica da fila de atendimento:
        // o que precisa de atenção agora não pode ficar escondido no fim.
        const ordenados = [...lista].sort(
          (a, b) => new Date(a.data_hora).getTime() - new Date(b.data_hora).getTime(),
        );
        setAgendamentos(ordenados);
        setClientes(clientesCarregados);
      })
      .catch(() => setErro("Não foi possível carregar a agenda."))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregarTudo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function nomeCliente(clienteId: string): string {
    return clientes.find((c) => c.id === clienteId)?.nome ?? clienteId;
  }

  async function handleStatus(agendamento: Agendamento, status: StatusAgendamento) {
    if (!token) return;
    setAtualizandoId(agendamento.id);
    try {
      await atualizarStatusAgendamento(agendamento, status, token);
      carregarTudo();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao atualizar.");
    } finally {
      setAtualizandoId(null);
    }
  }

  return (
    <div>
      <h2 className="mb-1 text-lg font-semibold text-gray-900">Agenda</h2>
      <p className="mb-4 text-xs text-gray-500">
        Visitas de avaliação presencial (dano estrutural etc.) — inclui as marcadas pela IA
        direto no chat.
      </p>

      {erro && <p className="mb-4 text-sm text-red-700">{erro}</p>}
      {carregando && !erro && <p className="text-sm text-gray-500">Carregando...</p>}
      {!carregando && !erro && agendamentos.length === 0 && (
        <p className="text-sm text-gray-500">Nenhum agendamento no momento.</p>
      )}

      {!carregando && !erro && agendamentos.length > 0 && (
        <div className="flex flex-col gap-3">
          {agendamentos.map((agendamento) => {
            const pendente = agendamento.status === "agendado" || agendamento.status === "confirmado";
            const atrasado = pendente && new Date(agendamento.data_hora).getTime() < Date.now();
            return (
              <div
                key={agendamento.id}
                className={`rounded-xl border bg-white p-4 shadow-sm ${
                  atrasado ? "border-red-300" : "border-gray-100"
                }`}
              >
                <div className="mb-2 flex items-center justify-between">
                  <p className="font-medium text-gray-900">{nomeCliente(agendamento.cliente_id)}</p>
                  <span
                    className={`text-xs font-medium ${atrasado ? "text-red-700" : "text-gray-400"}`}
                  >
                    {formatarDataHora(agendamento.data_hora)}
                  </span>
                </div>
                {agendamento.descricao && (
                  <p className="mb-2 text-sm text-gray-600">{agendamento.descricao}</p>
                )}
                <div className="flex items-center justify-between">
                  <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                    {ROTULOS_STATUS[agendamento.status]}
                  </span>
                  {pendente && (
                    <div className="flex gap-2">
                      {agendamento.status === "agendado" && (
                        <button
                          type="button"
                          disabled={atualizandoId === agendamento.id}
                          onClick={() => handleStatus(agendamento, "confirmado")}
                          className="rounded-lg bg-[#1a2332] px-3 py-1.5 text-xs font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
                        >
                          Confirmar
                        </button>
                      )}
                      <button
                        type="button"
                        disabled={atualizandoId === agendamento.id}
                        onClick={() => handleStatus(agendamento, "concluido")}
                        className="rounded-lg bg-green-700 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-green-800 disabled:opacity-60"
                      >
                        Concluir
                      </button>
                      <button
                        type="button"
                        disabled={atualizandoId === agendamento.id}
                        onClick={() => handleStatus(agendamento, "cancelado")}
                        className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
                      >
                        Cancelar
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
