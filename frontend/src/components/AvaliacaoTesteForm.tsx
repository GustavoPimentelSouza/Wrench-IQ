import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import {
  salvarAvaliacaoTeste,
  type ResultadoAvaliacao,
} from "../services/avaliacaoTesteService";

// TEMPORÁRIO (ferramenta de dev): avaliação manual da conversa do simulador.
// Sai inteiro apagando este arquivo + a linha que o usa no ChatSimuladorPage.

const OPCOES: { valor: ResultadoAvaliacao; rotulo: string; cor: string }[] = [
  { valor: "correto", rotulo: "Correto", cor: "bg-green-600 border-green-600" },
  { valor: "alucinou", rotulo: "Alucinou", cor: "bg-red-600 border-red-600" },
  { valor: "errou_fluxo", rotulo: "Errou o fluxo", cor: "bg-amber-500 border-amber-500" },
];

interface Props {
  telefone: string;
  // Usados no histórico: já abre com a avaliação salva e avisa a página
  // pra mover a conversa de aba. No simulador, ficam vazios.
  resultadoInicial?: ResultadoAvaliacao | null;
  comentarioInicial?: string | null;
  onSalvo?: (resultado: ResultadoAvaliacao, comentario: string | null) => void;
}

export function AvaliacaoTesteForm({
  telefone, resultadoInicial = null, comentarioInicial = null, onSalvo,
}: Props) {
  const { token } = useAuth();
  const [resultado, setResultado] = useState<ResultadoAvaliacao | null>(resultadoInicial);
  const [comentario, setComentario] = useState(comentarioInicial ?? "");
  const [status, setStatus] = useState<string | null>(null);

  async function handleSalvar(evento: FormEvent) {
    evento.preventDefault();
    if (!resultado || !token) return;
    try {
      await salvarAvaliacaoTeste(telefone, resultado, comentario, token);
      setStatus("✓ Avaliação salva");
      onSalvo?.(resultado, comentario.trim() || null);
    } catch (erro) {
      setStatus(erro instanceof Error ? erro.message : "Erro ao salvar.");
    }
  }

  return (
    <form onSubmit={handleSalvar} className="mt-4 rounded-xl border border-dashed border-gray-300 p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-gray-600">Avaliar esta conversa:</span>
        {OPCOES.map((opcao) => (
          <button
            key={opcao.valor}
            type="button"
            onClick={() => setResultado(opcao.valor)}
            className={`rounded-lg border px-3 py-1 font-medium transition ${
              resultado === opcao.valor
                ? `${opcao.cor} text-white`
                : "border-gray-300 text-gray-700 hover:bg-gray-50"
            }`}
          >
            {opcao.rotulo}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={comentario}
          onChange={(evento) => setComentario(evento.target.value)}
          placeholder="Comentário (opcional) — ex: 3ª resposta inventou o preço"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1a2332] focus:outline-none"
        />
        <button
          type="submit"
          disabled={!resultado}
          className="rounded-lg bg-[#1a2332] px-4 py-1.5 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-40"
        >
          Salvar
        </button>
      </div>
      {status && <p className="mt-2 text-xs text-gray-600">{status}</p>}
    </form>
  );
}
