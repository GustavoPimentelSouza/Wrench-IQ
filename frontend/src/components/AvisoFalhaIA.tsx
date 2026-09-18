import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { buscarStatusIA } from "../services/sistemaService";

const INTERVALO_MS = 30_000;

// Só pra este período de desenvolvimento (ver CLAUDE.md) — avisa na tela
// quando o classificador da IA cai no fallback silencioso (ex: modelo
// descontinuado pela Groq, como já aconteceu com o llama-3.1-8b-instant).
// Sem isso, essa falha não aparece em lugar nenhum.
export function AvisoFalhaIA() {
  const { token } = useAuth();
  const [visivel, setVisivel] = useState(false);
  const ultimaVista = useRef<string | null>(null);

  useEffect(() => {
    if (!token) return;

    async function checar() {
      try {
        const status = await buscarStatusIA(token!);
        if (
          status.falha_classificacao_em &&
          status.falha_classificacao_em !== ultimaVista.current
        ) {
          ultimaVista.current = status.falha_classificacao_em;
          setVisivel(true);
        }
      } catch {
        // Checagem de dev, silenciosa se falhar — não é crítica o
        // suficiente pra virar mais um alerta em cima do outro.
      }
    }

    checar();
    const id = setInterval(checar, INTERVALO_MS);
    return () => clearInterval(id);
  }, [token]);

  if (!visivel) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm rounded-lg bg-red-600 p-4 text-sm text-white shadow-lg">
      <p className="font-semibold">Falha na classificação da IA</p>
      <p className="mt-1 text-red-100">
        O classificador de mensagens falhou e caiu no modo de emergência
        (nao_identificado). Verifique os logs da API.
      </p>
      <button onClick={() => setVisivel(false)} className="mt-2 text-xs underline">
        Dispensar
      </button>
    </div>
  );
}
