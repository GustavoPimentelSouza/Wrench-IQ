import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  listarMensagensConversaTeste,
  type ConversaTeste,
  type MensagemTeste,
  type ResultadoAvaliacao,
} from "../services/avaliacaoTesteService";
import { AvaliacaoTesteForm } from "./AvaliacaoTesteForm";

// TEMPORÁRIO (ferramenta de dev): uma conversa do histórico, em acordeão —
// clica e expande as mensagens ali mesmo, sem trocar de página.

function formatarDataHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

interface Props {
  conversa: ConversaTeste;
  onAvaliada: (resultado: ResultadoAvaliacao, comentario: string | null) => void;
}

export function ConversaTesteLinha({ conversa, onAvaliada }: Props) {
  const { token } = useAuth();
  const [aberta, setAberta] = useState(false);
  // Só busca as mensagens na primeira vez que abre — lista pode ter centenas de conversas.
  const [mensagens, setMensagens] = useState<MensagemTeste[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function alternar() {
    setAberta((atual) => !atual);
    if (mensagens !== null || !token) return;
    try {
      setMensagens(await listarMensagensConversaTeste(conversa.cliente_id, token));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar mensagens.");
    }
  }

  return (
    <li className="rounded-xl border border-gray-100 bg-white shadow-sm">
      <button
        type="button"
        onClick={alternar}
        className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left text-sm"
      >
        <span className="font-mono text-gray-700">{conversa.telefone}</span>
        <span className="text-gray-500">{formatarDataHora(conversa.inicio)}</span>
        <span className="text-gray-500">{conversa.total_mensagens} mensagens</span>
        <span className="text-gray-400">{aberta ? "▲" : "▼"}</span>
      </button>

      {aberta && (
        <div className="flex flex-col gap-2 border-t border-gray-100 px-4 py-3">
          {erro && <p className="text-sm text-red-700">{erro}</p>}
          {mensagens === null && !erro && <p className="text-sm text-gray-400">Carregando...</p>}
          {mensagens?.map((mensagem, indice) => (
            <div key={indice} className="flex flex-col gap-1 text-sm">
              <p className="self-end rounded-2xl bg-[#1a2332] px-3 py-1.5 text-white">
                {mensagem.texto}
              </p>
              {mensagem.resposta_ia && (
                <p className="self-start rounded-2xl bg-gray-100 px-3 py-1.5 text-gray-900">
                  {mensagem.resposta_ia}
                </p>
              )}
              {mensagem.ferramentas_chamadas.length > 0 && (
                <p className="font-mono text-xs text-gray-500">
                  ↳ ferramenta: {mensagem.ferramentas_chamadas.join(", ")}
                </p>
              )}
            </div>
          ))}
          <AvaliacaoTesteForm
            telefone={conversa.telefone}
            resultadoInicial={conversa.resultado}
            comentarioInicial={conversa.comentario}
            onSalvo={onAvaliada}
          />
        </div>
      )}
    </li>
  );
}
