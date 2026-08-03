import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  listarAtendimentoPendente,
  resolverAtendimento,
  type MensagemAtendimento,
} from "../services/atendimentoService";
import { listarClientes } from "../services/clienteService";
import type { Cliente } from "../types/cliente";

// 1h de espera é o corte pra destacar como atrasado — no dia a dia da
// oficina, uma reclamação parada esse tempo já é grave o suficiente pra
// chamar atenção visual, não só aparecer na lista.
const LIMITE_ATRASO_MS = 60 * 60 * 1000;

function tempoDecorrido(criadoEm: string): string {
  const minutos = Math.floor((Date.now() - new Date(criadoEm).getTime()) / 60000);
  if (minutos < 60) return `${minutos} min atrás`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `${horas}h atrás`;
  return `${Math.floor(horas / 24)}d atrás`;
}

export function AtendimentoPage() {
  const { token } = useAuth();
  const [pendentes, setPendentes] = useState<MensagemAtendimento[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [resolvendoId, setResolvendoId] = useState<string | null>(null);

  function carregarTudo() {
    if (!token) return;
    setCarregando(true);
    Promise.all([listarAtendimentoPendente(token), listarClientes()])
      .then(([lista, clientesCarregados]) => {
        // Mais antigo primeiro — é o que mais precisa de atenção agora,
        // não o que chegou por último (senão o item esquecido de ontem
        // fica escondido no fim da lista).
        const ordenados = [...lista].sort(
          (a, b) => new Date(a.criado_em).getTime() - new Date(b.criado_em).getTime(),
        );
        setPendentes(ordenados);
        setClientes(clientesCarregados);
      })
      .catch(() => setErro("Não foi possível carregar a fila de atendimento."))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregarTudo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function nomeCliente(clienteId: string): string {
    return clientes.find((c) => c.id === clienteId)?.nome ?? clienteId;
  }

  async function handleResolver(mensagem: MensagemAtendimento) {
    if (!token) return;
    setResolvendoId(mensagem.id);
    try {
      await resolverAtendimento(mensagem.id, token);
      carregarTudo();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao resolver.");
    } finally {
      setResolvendoId(null);
    }
  }

  return (
    <div>
      <h2 className="mb-1 text-lg font-semibold text-gray-900">Atendimento humano</h2>
      <p className="mb-4 text-xs text-gray-500">
        Conversas que a IA não conseguiu resolver sozinha — reclamação sensível ou falha
        técnica (regra 4 do projeto). Mais antigas primeiro.
      </p>

      {erro && <p className="mb-4 text-sm text-red-700">{erro}</p>}
      {carregando && !erro && <p className="text-sm text-gray-500">Carregando...</p>}

      {!carregando && !erro && pendentes.length === 0 && (
        <p className="text-sm text-gray-500">Nenhuma conversa esperando atendimento agora.</p>
      )}

      {!carregando && !erro && pendentes.length > 0 && (
        <div className="flex flex-col gap-3">
          {pendentes.map((mensagem) => {
            const atrasado = Date.now() - new Date(mensagem.criado_em).getTime() > LIMITE_ATRASO_MS;
            return (
              <div
                key={mensagem.id}
                className={`rounded-xl border bg-white p-4 shadow-sm ${
                  atrasado ? "border-red-300" : "border-gray-100"
                }`}
              >
                <div className="mb-2 flex items-center justify-between">
                  <p className="font-medium text-gray-900">{nomeCliente(mensagem.cliente_id)}</p>
                  <span
                    className={`text-xs font-medium ${
                      atrasado ? "text-red-700" : "text-gray-400"
                    }`}
                  >
                    {tempoDecorrido(mensagem.criado_em)}
                  </span>
                </div>

                <p className="mb-2 inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {mensagem.categoria}
                </p>

                <p className="mb-1 text-sm text-gray-700">
                  <span className="font-medium">Cliente:</span> {mensagem.texto}
                </p>
                <p className="mb-3 text-sm text-gray-500">
                  <span className="font-medium">IA respondeu:</span>{" "}
                  {mensagem.resposta_ia ?? "(sem resposta)"}
                </p>

                <button
                  type="button"
                  disabled={resolvendoId === mensagem.id}
                  onClick={() => handleResolver(mensagem)}
                  className="rounded-lg bg-[#1a2332] px-3 py-1.5 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
                >
                  {resolvendoId === mensagem.id ? "Marcando..." : "Marcar resolvido"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
