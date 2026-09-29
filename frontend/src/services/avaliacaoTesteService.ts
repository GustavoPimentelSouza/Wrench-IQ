import { API_BASE_URL } from "./api";

// TEMPORÁRIO (ferramenta de dev): mesmos 3 eixos do eval automático
// (tests/eval_conversa/) — ver domain/avaliacao_teste.py no backend.
export type ResultadoAvaliacao = "correto" | "alucinou" | "errou_fluxo";

export async function salvarAvaliacaoTeste(
  telefone: string,
  resultado: ResultadoAvaliacao,
  comentario: string,
  token: string,
): Promise<void> {
  const resposta = await fetch(`${API_BASE_URL}/avaliacoes-teste`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ telefone, resultado, comentario }),
  });

  if (!resposta.ok) {
    // O backend manda o motivo em "detail" (ex: 404 = conversa sem mensagens).
    const corpo = await resposta.json().catch(() => null);
    throw new Error(corpo?.detail ?? "Não foi possível salvar a avaliação.");
  }
}

export interface ConversaTeste {
  cliente_id: string;
  telefone: string;
  inicio: string;
  fim: string;
  total_mensagens: number;
  resultado: ResultadoAvaliacao | null; // null = ainda não avaliada
  comentario: string | null;
}

export interface MensagemTeste {
  texto: string;
  resposta_ia: string | null;
  ferramentas_chamadas: string[];
  criado_em: string;
}

async function buscarJson<T>(caminho: string, token: string): Promise<T> {
  const resposta = await fetch(`${API_BASE_URL}${caminho}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resposta.ok) {
    throw new Error("Não foi possível carregar o histórico de testes.");
  }
  return resposta.json();
}

export function listarConversasTeste(token: string): Promise<ConversaTeste[]> {
  return buscarJson("/avaliacoes-teste/conversas", token);
}

export function listarMensagensConversaTeste(
  clienteId: string,
  token: string,
): Promise<MensagemTeste[]> {
  return buscarJson(`/avaliacoes-teste/conversas/${clienteId}/mensagens`, token);
}
