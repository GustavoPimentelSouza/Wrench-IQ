import { API_BASE_URL } from "./api";
import type { Protocolo } from "../types/protocolo";

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
