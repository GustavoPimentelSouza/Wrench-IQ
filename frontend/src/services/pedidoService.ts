import { API_BASE_URL } from "./api";
import type { Pedido, PedidoCreateInput, StatusPedido } from "../types/pedido";

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

export async function listarPedidos(
  token: string,
  status?: StatusPedido,
): Promise<Pedido[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const resposta = await fetch(`${API_BASE_URL}/pedidos${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resposta.ok) {
    return extrairErro(resposta, "Não foi possível carregar os pedidos.");
  }

  return resposta.json();
}

export async function criarPedido(
  dados: PedidoCreateInput,
  token: string,
): Promise<Pedido> {
  const resposta = await fetch(`${API_BASE_URL}/pedidos`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dados),
  });

  if (!resposta.ok) {
    return extrairErro(resposta, "Não foi possível criar o pedido.");
  }

  return resposta.json();
}

async function transicao(pedidoId: string, acao: string, token: string): Promise<Pedido> {
  const resposta = await fetch(`${API_BASE_URL}/pedidos/${pedidoId}/${acao}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resposta.ok) {
    return extrairErro(resposta, "Não foi possível atualizar o pedido.");
  }

  return resposta.json();
}

export const confirmarPagamento = (id: string, token: string) =>
  transicao(id, "confirmar-pagamento", token);

export const confirmarConferencia = (id: string, token: string) =>
  transicao(id, "confirmar-conferencia", token);

export const marcarEntregue = (id: string, token: string) =>
  transicao(id, "marcar-entregue", token);

export const cancelarPedido = (id: string, token: string) =>
  transicao(id, "cancelar", token);
