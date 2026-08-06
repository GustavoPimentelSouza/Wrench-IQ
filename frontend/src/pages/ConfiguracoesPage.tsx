import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  atualizarConfiguracaoOficina,
  buscarConfiguracaoOficina,
} from "../services/configuracaoOficinaService";
import type { ConfiguracaoOficina } from "../types/configuracaoOficina";

// Input type="time" só aceita "HH:MM", mas a API devolve "HH:MM:SS" — corta
// os segundos na entrada e completa de volta na saída.
function paraInput(horario: string | null): string {
  return horario ? horario.slice(0, 5) : "";
}

interface FormularioDia {
  fechado: boolean;
  abertura: string;
  fechamento: string;
}

function diaInicial(abertura: string | null, fechamento: string | null): FormularioDia {
  return { fechado: abertura === null, abertura: paraInput(abertura) || "08:00", fechamento: paraInput(fechamento) || "18:00" };
}

interface BlocoDiaProps {
  titulo: string;
  permiteFechar?: boolean;
  dia: FormularioDia;
  onChange: (dia: FormularioDia) => void;
}

function BlocoDia({ titulo, permiteFechar = true, dia, onChange }: BlocoDiaProps) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <p className="font-medium text-gray-900">{titulo}</p>
        {permiteFechar && (
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={dia.fechado}
              onChange={(evento) => onChange({ ...dia, fechado: evento.target.checked })}
            />
            Fechado
          </label>
        )}
      </div>
      {!dia.fechado && (
        <div className="flex items-center gap-3">
          <input
            type="time"
            value={dia.abertura}
            onChange={(evento) => onChange({ ...dia, abertura: evento.target.value })}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm"
          />
          <span className="text-sm text-gray-500">às</span>
          <input
            type="time"
            value={dia.fechamento}
            onChange={(evento) => onChange({ ...dia, fechamento: evento.target.value })}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm"
          />
        </div>
      )}
    </div>
  );
}

export function ConfiguracoesPage() {
  const { token } = useAuth();
  const [nomeEmpresa, setNomeEmpresa] = useState("");
  const [endereco, setEndereco] = useState("");
  const [mensagemEncerramento, setMensagemEncerramento] = useState("");
  const [semana, setSemana] = useState<FormularioDia>(diaInicial("08:00", "19:00"));
  const [sabado, setSabado] = useState<FormularioDia>(diaInicial("08:00", "18:00"));
  const [domingo, setDomingo] = useState<FormularioDia>(diaInicial("08:00", "12:00"));
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState(false);

  useEffect(() => {
    buscarConfiguracaoOficina()
      .then((config) => {
        setNomeEmpresa(config.nome_empresa);
        setEndereco(config.endereco ?? "");
        setMensagemEncerramento(config.mensagem_encerramento ?? "");
        setSemana(diaInicial(config.horario_semana_abertura, config.horario_semana_fechamento));
        setSabado(diaInicial(config.horario_sabado_abertura, config.horario_sabado_fechamento));
        setDomingo(diaInicial(config.horario_domingo_abertura, config.horario_domingo_fechamento));
      })
      .catch(() => setErro("Não foi possível carregar a configuração."))
      .finally(() => setCarregando(false));
  }, []);

  function paraPayload(dia: FormularioDia): { abertura: string | null; fechamento: string | null } {
    if (dia.fechado) return { abertura: null, fechamento: null };
    return { abertura: dia.abertura, fechamento: dia.fechamento };
  }

  async function handleSalvar() {
    if (!token) return;
    setSalvando(true);
    setErro(null);
    setSucesso(false);
    const sab = paraPayload(sabado);
    const dom = paraPayload(domingo);
    const payload: ConfiguracaoOficina = {
      nome_empresa: nomeEmpresa,
      endereco: endereco.trim() || null,
      mensagem_encerramento: mensagemEncerramento.trim() || null,
      horario_semana_abertura: semana.abertura,
      horario_semana_fechamento: semana.fechamento,
      horario_sabado_abertura: sab.abertura,
      horario_sabado_fechamento: sab.fechamento,
      horario_domingo_abertura: dom.abertura,
      horario_domingo_fechamento: dom.fechamento,
    };
    try {
      await atualizarConfiguracaoOficina(payload, token);
      setSucesso(true);
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao salvar.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div>
      <h2 className="mb-1 text-lg font-semibold text-gray-900">Configurações da oficina</h2>
      <p className="mb-4 text-xs text-gray-500">
        Esses dados são o que a IA usa nas respostas do WhatsApp — mantenha atualizado, ela nunca
        inventa informação que não estiver aqui.
      </p>

      {carregando && <p className="text-sm text-gray-500">Carregando...</p>}

      {!carregando && (
        <div className="flex max-w-md flex-col gap-3">
          <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
            <label className="mb-1 block text-sm font-medium text-gray-900">
              Nome da oficina
            </label>
            <input
              type="text"
              value={nomeEmpresa}
              onChange={(evento) => setNomeEmpresa(evento.target.value)}
              placeholder="Ex: Oficina Dugrau"
              className="mb-3 w-full rounded-lg border border-gray-200 px-3 py-1.5 text-sm"
            />
            <label className="mb-1 block text-sm font-medium text-gray-900">Endereço</label>
            <input
              type="text"
              value={endereco}
              onChange={(evento) => setEndereco(evento.target.value)}
              placeholder="Ex: Rua das Oficinas, 123 - Centro"
              className="mb-3 w-full rounded-lg border border-gray-200 px-3 py-1.5 text-sm"
            />
            <label className="mb-1 block text-sm font-medium text-gray-900">
              Mensagem de encerramento
            </label>
            <input
              type="text"
              value={mensagemEncerramento}
              onChange={(evento) => setMensagemEncerramento(evento.target.value)}
              placeholder="Ex: Agradecemos seu contato!"
              className="w-full rounded-lg border border-gray-200 px-3 py-1.5 text-sm"
            />
          </div>

          <BlocoDia titulo="Segunda a sexta" permiteFechar={false} dia={semana} onChange={setSemana} />
          <BlocoDia titulo="Sábado" dia={sabado} onChange={setSabado} />
          <BlocoDia titulo="Domingo" dia={domingo} onChange={setDomingo} />

          {erro && <p className="text-sm text-red-700">{erro}</p>}
          {sucesso && <p className="text-sm text-green-700">Configuração salva.</p>}

          <button
            type="button"
            disabled={salvando}
            onClick={handleSalvar}
            className="mt-2 self-start rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Salvar"}
          </button>
        </div>
      )}
    </div>
  );
}
