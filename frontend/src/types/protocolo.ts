export type StatusProtocolo =
  | "aguardando_aprovacao"
  | "em_execucao"
  | "pronto"
  | "cancelado";

export interface Protocolo {
  id: string;
  numero: number;
  cliente_id: string;
  veiculo: string;
  categoria: string;
  status: StatusProtocolo;
  descricao: string | null;
  mecanico_id: string | null;
  criado_em: string;
  atualizado_em: string;
}
