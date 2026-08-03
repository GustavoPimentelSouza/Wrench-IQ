import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { atualizarPeca, excluirPeca } from "../services/pecaService";
import type { Peca, PecaCreateInput } from "../types/peca";
import { CamposPeca } from "./CamposPeca";

function paraFormulario(peca: Peca): PecaCreateInput {
  return {
    nome: peca.nome,
    marca_modelo_compativel: peca.marca_modelo_compativel,
    ano_compativel: peca.ano_compativel,
    preco: peca.preco,
    quantidade_estoque: peca.quantidade_estoque,
    imagem_url: peca.imagem_url ?? "",
  };
}

function formatarPreco(preco: string): string {
  return Number(preco).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface PecaLinhaProps {
  peca: Peca;
  onAtualizada: () => void;
}

export function PecaLinha({ peca, onAtualizada }: PecaLinhaProps) {
  const { token } = useAuth();
  const [editando, setEditando] = useState(false);
  const [valores, setValores] = useState<PecaCreateInput>(() => paraFormulario(peca));
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [excluindo, setExcluindo] = useState(false);

  function iniciarEdicao() {
    setValores(paraFormulario(peca));
    setErro(null);
    setEditando(true);
  }

  async function handleSalvar(evento: FormEvent) {
    evento.preventDefault();
    if (!token) {
      setErro("Faça login novamente para editar peças.");
      return;
    }

    setSalvando(true);
    setErro(null);
    try {
      await atualizarPeca(peca.id, valores, token);
      setEditando(false);
      onAtualizada();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao atualizar peça.");
    } finally {
      setSalvando(false);
    }
  }

  async function handleExcluir() {
    if (!token) {
      setErro("Faça login novamente para excluir peças.");
      return;
    }
    const confirmado = window.confirm(`Excluir a peça "${peca.nome}"? Essa ação não pode ser desfeita.`);
    if (!confirmado) return;

    setExcluindo(true);
    try {
      await excluirPeca(peca.id, token);
      onAtualizada();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao excluir peça.");
    } finally {
      setExcluindo(false);
    }
  }

  if (editando) {
    return (
      <form
        onSubmit={handleSalvar}
        className="grid grid-cols-1 gap-3 rounded-xl border border-[#1a2332] bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-6"
      >
        <CamposPeca valores={valores} aoMudar={setValores} />

        {erro && <p className="col-span-full text-sm text-red-700">{erro}</p>}

        <div className="col-span-full flex gap-2">
          <button
            type="submit"
            disabled={salvando}
            className="rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Salvar"}
          </button>
          <button
            type="button"
            onClick={() => setEditando(false)}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
          >
            Cancelar
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      {peca.imagem_url ? (
        <img
          src={peca.imagem_url}
          alt={peca.nome}
          className="h-12 w-12 shrink-0 rounded-lg object-cover"
        />
      ) : (
        <div className="h-12 w-12 shrink-0 rounded-lg bg-gray-100" />
      )}

      <div className="flex-1">
        <p className="font-medium text-gray-900">{peca.nome}</p>
        <p className="text-sm text-gray-500">
          {peca.marca_modelo_compativel} · {peca.ano_compativel}
        </p>
        {erro && <p className="text-sm text-red-700">{erro}</p>}
      </div>

      <div className="text-right text-sm text-gray-600">
        <p>{formatarPreco(peca.preco)}</p>
        <p>{peca.quantidade_estoque} em estoque</p>
      </div>

      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={iniciarEdicao}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
        >
          Editar
        </button>
        <button
          type="button"
          onClick={handleExcluir}
          disabled={excluindo}
          className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
        >
          {excluindo ? "Excluindo..." : "Excluir"}
        </button>
      </div>
    </div>
  );
}
