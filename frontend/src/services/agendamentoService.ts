import { API_BASE_URL } from "./api";
import type { Agendamento, StatusAgendamento } from "../types/agendamento";

async function extrairErro(resposta: Response, mensagemPadrao: string): Promise<never> {
  if (resposta.status === 401) {
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  let detalhe: string | undefined;
  try {
    const corpo = await resposta.json();
    if (typeof corpo?.detail === "string") {
      detalhe = corpo.detail;
    }
  } catch {
    // corpo não é JSON válido, ignora e usa a mensagem padrão
  }

  throw new Error(detalhe ?? mensagemPadrao);
}

// Sem cliente_id: todos os agendamentos, de todos os clientes — é a visão
// que a AgendaPage usa (a oficina inteira, não um cliente por vez).
export async function listarAgendamentos(): Promise<Agendamento[]> {
  const resposta = await fetch(`${API_BASE_URL}/agendamentos`);

  if (!resposta.ok) {
    throw new Error("Não foi possível carregar a agenda.");
  }

  return resposta.json();
}

export async function atualizarStatusAgendamento(
  agendamento: Agendamento,
  status: StatusAgendamento,
  token: string,
): Promise<Agendamento> {
  const resposta = await fetch(`${API_BASE_URL}/agendamentos/${agendamento.id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ data_hora: agendamento.data_hora, status }),
  });

  if (!resposta.ok) {
    return extrairErro(resposta, "Não foi possível atualizar o agendamento.");
  }

  return resposta.json();
}
