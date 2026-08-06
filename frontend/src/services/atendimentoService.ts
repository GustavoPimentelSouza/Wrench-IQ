import { API_BASE_URL } from "./api";

export type MotivoAtendimento = "falha_tecnica" | "reclamacao_sensivel" | "transferencia_ia";

export interface MensagemAtendimento {
  id: string;
  cliente_id: string;
  texto: string;
  categoria: string;
  resposta_ia: string | null;
  motivo_atendimento: MotivoAtendimento | null;
  criado_em: string;
}

async function tratarErroResposta(resposta: Response, mensagemPadrao: string): Promise<never> {
  if (resposta.status === 401) {
    throw new Error("Sessão expirada. Faça login novamente.");
  }
  throw new Error(mensagemPadrao);
}

export async function listarAtendimentoPendente(token: string): Promise<MensagemAtendimento[]> {
  const resposta = await fetch(`${API_BASE_URL}/mensagens/atendimento-pendente`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resposta.ok) {
    return tratarErroResposta(resposta, "Não foi possível carregar a fila de atendimento.");
  }

  return resposta.json();
}

export async function resolverAtendimento(id: string, token: string): Promise<void> {
  const resposta = await fetch(`${API_BASE_URL}/mensagens/${id}/resolver-atendimento`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resposta.ok) {
    await tratarErroResposta(resposta, "Não foi possível marcar como resolvido.");
  }
}
