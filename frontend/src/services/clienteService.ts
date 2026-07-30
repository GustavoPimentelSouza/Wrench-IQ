import { API_BASE_URL } from "./api";
import type { Cliente, ClienteCreateInput } from "../types/cliente";

async function tratarErroResposta(resposta: Response, mensagemPadrao: string): Promise<never> {
  if (resposta.status === 401) {
    throw new Error("Sessão expirada. Faça login novamente.");
  }
  if (resposta.status === 409) {
    throw new Error("Não é possível excluir: cliente tem protocolos vinculados.");
  }

  let mensagem: string | undefined;
  try {
    const corpo = await resposta.json();
    if (typeof corpo?.detail === "string") {
      mensagem = corpo.detail;
    } else if (Array.isArray(corpo?.detail) && typeof corpo.detail[0]?.msg === "string") {
      mensagem = corpo.detail[0].msg;
    }
  } catch {
    // corpo não é JSON válido, ignora e usa a mensagem padrão
  }

  throw new Error(mensagem ?? mensagemPadrao);
}

export async function listarClientes(): Promise<Cliente[]> {
  const resposta = await fetch(`${API_BASE_URL}/clientes`);

  if (!resposta.ok) {
    throw new Error("Não foi possível carregar os clientes.");
  }

  return resposta.json();
}

export async function criarCliente(
  dados: ClienteCreateInput,
  token: string,
): Promise<Cliente> {
  const resposta = await fetch(`${API_BASE_URL}/clientes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dados),
  });

  if (!resposta.ok) {
    await tratarErroResposta(resposta, "Não foi possível cadastrar o cliente.");
  }

  return resposta.json();
}

export async function atualizarCliente(
  id: string,
  dados: ClienteCreateInput,
  token: string,
): Promise<Cliente> {
  const resposta = await fetch(`${API_BASE_URL}/clientes/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dados),
  });

  if (!resposta.ok) {
    await tratarErroResposta(resposta, "Não foi possível atualizar o cliente.");
  }

  return resposta.json();
}

export async function excluirCliente(id: string, token: string): Promise<void> {
  const resposta = await fetch(`${API_BASE_URL}/clientes/${id}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!resposta.ok) {
    await tratarErroResposta(resposta, "Não foi possível excluir o cliente.");
  }
}
