export interface Cliente {
  id: string;
  nome: string;
  telefone: string;
  email: string | null;
  criado_em: string;
}

export interface ClienteCreateInput {
  nome: string;
  telefone: string;
  email?: string | null;
}
