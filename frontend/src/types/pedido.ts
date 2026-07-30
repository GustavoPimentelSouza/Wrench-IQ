export type TipoEntrega = "retirada_local" | "envio_remoto";

export type StatusPedido =
  | "aguardando_pagamento"
  | "aguardando_retirada"
  | "aguardando_conferencia"
  | "despachado"
  | "entregue"
  | "cancelado";

export interface Pedido {
  id: string;
  numero: number;
  cliente_id: string;
  peca_id: string;
  quantidade: number;
  valor_total: string;
  tipo_entrega: TipoEntrega;
  status: StatusPedido;
  endereco_entrega: string | null;
  link_pagamento: string | null;
  criado_em: string;
  entregue_em: string | null;
  dentro_do_prazo_arrependimento: boolean;
}

export interface PedidoCreateInput {
  cliente_id: string;
  peca_id: string;
  quantidade: number;
  tipo_entrega: TipoEntrega;
  endereco_entrega?: string;
}
