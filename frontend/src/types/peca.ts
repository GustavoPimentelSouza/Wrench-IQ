export interface Peca {
  id: string;
  nome: string;
  marca_modelo_compativel: string;
  ano_compativel: string;
  preco: string;
  quantidade_estoque: number;
  quantidade_minima: number;
  imagem_url: string | null;
  // Nem toda peça tem variação de cor (ex: vela, cabo) — por isso opcional.
  cor: string | null;
  criado_em: string;
}

export interface PecaCreateInput {
  nome: string;
  marca_modelo_compativel: string;
  ano_compativel: string;
  preco: string;
  quantidade_estoque: number;
  imagem_url?: string | null;
  cor?: string | null;
}
