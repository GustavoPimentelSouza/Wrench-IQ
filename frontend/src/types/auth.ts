export interface LoginRequest {
  email: string;
  senha: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UsuarioAutenticado {
  id: string;
  papel: string;
}
