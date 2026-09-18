import { API_BASE_URL } from "./api";

export interface StatusIA {
  falha_classificacao_em: string | null;
}

export async function buscarStatusIA(token: string): Promise<StatusIA> {
  const resposta = await fetch(`${API_BASE_URL}/sistema/status-ia`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resposta.ok) {
    throw new Error("Não foi possível checar o status da IA.");
  }

  return resposta.json();
}
