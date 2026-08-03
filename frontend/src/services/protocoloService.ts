import { API_BASE_URL } from "./api";
import type { Protocolo, ProtocoloCreateInput } from "../types/protocolo";

interface ProtocoloUpdateInput {
  veiculo: string;
  categoria: string;
  descricao?: string | null;
  mecanico_id?: string | null;
  valor_orcamento?: string | null;
}

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

export async function listarProtocolos(): Promise<Protocolo[]> {
  const resposta = await fetch(`${API_BASE_URL}/protocolos`);

  if (!resposta.ok) {
    throw new Error("Não foi possível carregar os protocolos.");
  }

  return resposta.json();
}

export async function listarProtocolosDoCliente(clienteId: string): Promise<Protocolo[]> {
  const resposta = await fetch(
    `${API_BASE_URL}/protocolos?cliente_id=${encodeURIComponent(clienteId)}`,
  );

  if (!resposta.ok) {
    throw new Error("Não foi possível carregar o histórico do cliente.");
  }

  return resposta.json();
}

export async function criarProtocolo(
  dados: ProtocoloCreateInput,
  token: string,
): Promise<Protocolo> {
  const resposta = await fetch(`${API_BASE_URL}/protocolos`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dados),
  });

  if (!resposta.ok) {
    return extrairErro(resposta, "Não foi possível criar o protocolo.");
  }

  return resposta.json();
}

export async function atualizarProtocolo(
  id: string,
  dados: ProtocoloUpdateInput,
  token: string,
): Promise<Protocolo> {
  const resposta = await fetch(`${API_BASE_URL}/protocolos/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dados),
  });

  if (!resposta.ok) {
    return extrairErro(resposta, "Não foi possível atualizar o protocolo.");
  }

  return resposta.json();
}

async function transicao(
  protocoloId: string,
  acao: string,
  token: string,
  corpo?: Record<string, unknown>,
): Promise<Protocolo> {
  const resposta = await fetch(`${API_BASE_URL}/protocolos/${protocoloId}/${acao}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(corpo ?? {}),
  });

  if (!resposta.ok) {
    return extrairErro(resposta, "Não foi possível atualizar o protocolo.");
  }

  return resposta.json();
}

export const aprovarProtocolo = (id: string, token: string) => transicao(id, "aprovar", token);

export const concluirProtocolo = (id: string, token: string) => transicao(id, "concluir", token);

export const cancelarProtocolo = (id: string, token: string, motivo?: string) =>
  transicao(id, "cancelar", token, { motivo });
