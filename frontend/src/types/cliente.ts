// endereco já existia no backend (domain/cliente.py) mas nunca tinha sido
// exposto aqui — sem isso, a tela de Clientes não tinha como mostrar nem
// editar esse dado (parte do "cadastro completo" discutido no dia a dia).
export interface Cliente {
  id: string;
  nome: string;
  telefone: string;
  email: string | null;
  endereco: string | null;
  criado_em: string;
}

export interface ClienteCreateInput {
  nome: string;
  telefone: string;
  email?: string | null;
  endereco?: string | null;
}
