export type StatusAgendamento = "agendado" | "confirmado" | "cancelado" | "concluido";

export interface Agendamento {
  id: string;
  cliente_id: string;
  data_hora: string;
  status: StatusAgendamento;
  criado_em: string;
  descricao: string | null;
}
