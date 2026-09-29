import { useEffect, useState } from "react";
import { ConversaTesteLinha } from "../components/ConversaTesteLinha";
import { useAuth } from "../context/AuthContext";
import {
  listarConversasTeste,
  type ConversaTeste,
  type ResultadoAvaliacao,
} from "../services/avaliacaoTesteService";

// TEMPORÁRIO (ferramenta de dev): histórico das conversas do simulador,
// separado pela avaliação manual. Sai apagando esta página, o
// ConversaTesteLinha e a rota/item de menu "/historico-testes".

type Aba = ResultadoAvaliacao | "nao_avaliada";

const ABAS: { valor: Aba; rotulo: string }[] = [
  { valor: "correto", rotulo: "Correto" },
  { valor: "alucinou", rotulo: "Alucinou" },
  { valor: "errou_fluxo", rotulo: "Errou o fluxo" },
  { valor: "nao_avaliada", rotulo: "Não avaliadas" },
];

export function HistoricoTestesPage() {
  const { token } = useAuth();
  const [conversas, setConversas] = useState<ConversaTeste[]>([]);
  const [aba, setAba] = useState<Aba>("nao_avaliada");
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    listarConversasTeste(token)
      .then(setConversas)
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro ao carregar."));
  }, [token]);

  // Atualiza só na tela (o backend já salvou) — a conversa muda de aba na hora.
  function marcarAvaliada(clienteId: string, resultado: ResultadoAvaliacao, comentario: string | null) {
    setConversas((atual) =>
      atual.map((c) => (c.cliente_id === clienteId ? { ...c, resultado, comentario } : c)),
    );
  }

  const doResultado = (valor: Aba) =>
    conversas.filter((c) => (c.resultado ?? "nao_avaliada") === valor);

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Histórico de testes (IA)</h2>

      <div className="mb-4 flex flex-wrap gap-2">
        {ABAS.map((item) => (
          <button
            key={item.valor}
            type="button"
            onClick={() => setAba(item.valor)}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
              aba === item.valor
                ? "border-[#1a2332] bg-[#1a2332] text-white"
                : "border-gray-300 text-gray-700 hover:bg-gray-50"
            }`}
          >
            {item.rotulo} ({doResultado(item.valor).length})
          </button>
        ))}
      </div>

      {erro && <p className="mb-2 text-sm text-red-700">{erro}</p>}

      <ul className="flex flex-col gap-2">
        {doResultado(aba).map((conversa) => (
          <ConversaTesteLinha
            key={conversa.cliente_id}
            conversa={conversa}
            onAvaliada={(resultado, comentario) =>
              marcarAvaliada(conversa.cliente_id, resultado, comentario)
            }
          />
        ))}
      </ul>
    </div>
  );
}
