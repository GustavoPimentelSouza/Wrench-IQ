import { API_BASE_URL } from "./api";
import type { ConfiguracaoOficina } from "../types/configuracaoOficina";

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

export async function buscarConfiguracaoOficina(): Promise<ConfiguracaoOficina> {
  const resposta = await fetch(`${API_BASE_URL}/configuracao-oficina`);

  if (!resposta.ok) {
    throw new Error("Não foi possível carregar a configuração da oficina.");
  }

  return resposta.json();
}

export async function atualizarConfiguracaoOficina(
  dados: ConfiguracaoOficina,
  token: string,
): Promise<ConfiguracaoOficina> {
  const resposta = await fetch(`${API_BASE_URL}/configuracao-oficina`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dados),
  });

  if (!resposta.ok) {
    return extrairErro(resposta, "Não foi possível salvar a configuração.");
  }

  return resposta.json();
}
