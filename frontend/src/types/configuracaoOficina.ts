export interface ConfiguracaoOficina {
  horario_semana_abertura: string;
  horario_semana_fechamento: string;
  horario_sabado_abertura: string | null;
  horario_sabado_fechamento: string | null;
  horario_domingo_abertura: string | null;
  horario_domingo_fechamento: string | null;
}
