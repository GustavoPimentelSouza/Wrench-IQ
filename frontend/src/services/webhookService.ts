import { API_BASE_URL } from "./api";

export interface RespostaWebhook {
  resposta: string;
  ferramentas_chamadas: string[];
  imagem_url: string | null;
}

export async function enviarMensagemSimulada(
  telefone: string,
  mensagem: string,
): Promise<RespostaWebhook> {
  const resposta = await fetch(`${API_BASE_URL}/webhook`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ telefone, mensagem }),
  });

  if (!resposta.ok) {
    throw new Error("Não foi possível enviar a mensagem.");
  }

  return resposta.json();
}
