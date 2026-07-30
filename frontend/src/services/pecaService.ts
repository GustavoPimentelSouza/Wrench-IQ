import { API_BASE_URL } from "./api";
import type { Peca, PecaCreateInput } from "../types/peca";

function tratarErroResposta(resposta: Response, mensagemPadrao: string): never {
  if (resposta.status === 401) {
    throw new Error("Sessão expirada. Faça login novamente.");
  }
  throw new Error(mensagemPadrao);
}

export async function listarPecas(): Promise<Peca[]> {
  const resposta = await fetch(`${API_BASE_URL}/pecas`);

  if (!resposta.ok) {
    throw new Error("Não foi possível carregar as peças.");
  }

  return resposta.json();
}

export async function criarPeca(dados: PecaCreateInput, token: string): Promise<Peca> {
  const resposta = await fetch(`${API_BASE_URL}/pecas`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dados),
  });

  if (!resposta.ok) {
    tratarErroResposta(resposta, "Não foi possível cadastrar a peça.");
  }

  return resposta.json();
}

export async function atualizarPeca(
  id: string,
  dados: PecaCreateInput,
  token: string,
): Promise<Peca> {
  const resposta = await fetch(`${API_BASE_URL}/pecas/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dados),
  });

  if (!resposta.ok) {
    tratarErroResposta(resposta, "Não foi possível atualizar a peça.");
  }

  return resposta.json();
}

export async function excluirPeca(id: string, token: string): Promise<void> {
  const resposta = await fetch(`${API_BASE_URL}/pecas/${id}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!resposta.ok) {
    tratarErroResposta(resposta, "Não foi possível excluir a peça.");
  }
}
