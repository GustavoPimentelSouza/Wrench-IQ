import { useState, type FormEvent } from "react";
import { enviarMensagemSimulada } from "../services/webhookService";

interface MensagemChat {
  autor: "cliente" | "ia";
  texto: string;
  ferramentas?: string[];
  imagemUrl?: string | null;
}

function gerarTelefoneDeTeste(): string {
  const numero = Math.floor(Math.random() * 1e8)
    .toString()
    .padStart(8, "0");
  return `5599${numero}`;
}

export function ChatSimuladorPage() {
  const [telefone, setTelefone] = useState(gerarTelefoneDeTeste);
  const [mensagens, setMensagens] = useState<MensagemChat[]>([]);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function novaConversa() {
    setTelefone(gerarTelefoneDeTeste());
    setMensagens([]);
    setErro(null);
  }

  async function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    if (!texto.trim()) return;

    const mensagemCliente: MensagemChat = { autor: "cliente", texto };
    setMensagens((atual) => [...atual, mensagemCliente]);
    setTexto("");
    setEnviando(true);
    setErro(null);

    try {
      const resultado = await enviarMensagemSimulada(telefone, texto);
      setMensagens((atual) => [
        ...atual,
        {
          autor: "ia",
          texto: resultado.resposta,
          ferramentas: resultado.ferramentas_chamadas,
          imagemUrl: resultado.imagem_url,
        },
      ]);
    } catch {
      setErro("Não foi possível falar com a IA agora.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Simulador de conversa</h2>
          <p className="text-xs text-gray-500">
            Cliente simulado: <span className="font-mono">{telefone}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={novaConversa}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
        >
          Nova conversa
        </button>
      </div>

      <div className="mb-4 flex min-h-[400px] flex-col gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
        {mensagens.length === 0 && (
          <p className="text-sm text-gray-400">
            Manda uma mensagem como se fosse um cliente perguntando sobre uma peça.
          </p>
        )}

        {mensagens.map((mensagem, indice) => (
          <div
            key={indice}
            className={`flex ${mensagem.autor === "cliente" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                mensagem.autor === "cliente"
                  ? "bg-[#1a2332] text-white"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              <p>{mensagem.texto}</p>
              {mensagem.imagemUrl && (
                <img
                  src={mensagem.imagemUrl}
                  alt="Peça encontrada"
                  className="mt-2 h-40 w-40 rounded-lg border border-gray-200 bg-white object-contain p-2"
                />
              )}
              {mensagem.ferramentas && mensagem.ferramentas.length > 0 && (
                <p className="mt-1 font-mono text-xs text-gray-500">
                  ↳ ferramenta: {mensagem.ferramentas.join(", ")}
                </p>
              )}
            </div>
          </div>
        ))}

        {enviando && <p className="text-sm text-gray-400">IA está digitando...</p>}
      </div>

      {erro && <p className="mb-2 text-sm text-red-700">{erro}</p>}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          placeholder="Digite como se fosse o cliente..."
          disabled={enviando}
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
        />
        <button
          type="submit"
          disabled={enviando}
          className="rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
