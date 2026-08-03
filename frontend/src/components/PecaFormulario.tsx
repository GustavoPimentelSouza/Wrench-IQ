import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { criarPeca } from "../services/pecaService";
import type { PecaCreateInput } from "../types/peca";
import { CamposPeca } from "./CamposPeca";

const CAMPOS_VAZIOS: PecaCreateInput = {
  nome: "",
  marca_modelo_compativel: "",
  ano_compativel: "",
  preco: "",
  quantidade_estoque: 0,
  imagem_url: "",
};

interface PecaFormularioProps {
  onCriada: () => void;
}

export function PecaFormulario({ onCriada }: PecaFormularioProps) {
  const { token } = useAuth();
  const [novaPeca, setNovaPeca] = useState<PecaCreateInput>(CAMPOS_VAZIOS);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);

    if (!token) {
      setErro("Faça login novamente para cadastrar peças.");
      return;
    }

    setEnviando(true);
    try {
      await criarPeca(novaPeca, token);
      setNovaPeca(CAMPOS_VAZIOS);
      onCriada();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao cadastrar peça.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-8 grid grid-cols-1 gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-6"
    >
      <CamposPeca valores={novaPeca} aoMudar={setNovaPeca} />

      {erro && <p className="col-span-full text-sm text-red-700">{erro}</p>}

      <button
        type="submit"
        disabled={enviando}
        className="col-span-full w-fit rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
      >
        {enviando ? "Cadastrando..." : "Cadastrar peça"}
      </button>
    </form>
  );
}
