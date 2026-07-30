import { API_BASE_URL } from "./api";
import type { LoginRequest, LoginResponse } from "../types/auth";

export class CredenciaisInvalidasError extends Error {}

export async function login(dados: LoginRequest): Promise<LoginResponse> {
  let resposta: Response;
  try {
    resposta = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    });
  } catch {
    throw new Error("Não foi possível conectar ao servidor.");
  }

  if (resposta.status === 401) {
    throw new CredenciaisInvalidasError("E-mail ou senha inválidos.");
  }

  if (!resposta.ok) {
    throw new Error("Não foi possível conectar ao servidor.");
  }

  return resposta.json();
}
