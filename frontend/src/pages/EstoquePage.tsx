import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { atualizarPeca, criarPeca, excluirPeca, listarPecas } from "../services/pecaService";
import type { Peca, PecaCreateInput } from "../types/peca";

const CAMPOS_VAZIOS: PecaCreateInput = {
  nome: "",
  marca_modelo_compativel: "",
  ano_compativel: "",
  preco: "",
  quantidade_estoque: 0,
  imagem_url: "",
};

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

interface CamposPecaProps {
  valores: PecaCreateInput;
  aoMudar: (valores: PecaCreateInput) => void;
}

function CamposPeca({ valores, aoMudar }: CamposPecaProps) {
  return (
    <>
      <input
        value={valores.nome}
        onChange={(evento) => aoMudar({ ...valores, nome: evento.target.value })}
        placeholder="Nome"
        required
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
      <input
        value={valores.marca_modelo_compativel}
        onChange={(evento) =>
          aoMudar({ ...valores, marca_modelo_compativel: evento.target.value })
        }
        placeholder="Marca/modelo compatível"
        required
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
      <input
        value={valores.ano_compativel}
        onChange={(evento) => aoMudar({ ...valores, ano_compativel: evento.target.value })}
        placeholder="Ano compatível"
        required
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
      <input
        value={valores.preco}
        onChange={(evento) => aoMudar({ ...valores, preco: evento.target.value })}
        placeholder="Preço"
        required
        inputMode="decimal"
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
      <input
        value={valores.quantidade_estoque}
        onChange={(evento) =>
          aoMudar({ ...valores, quantidade_estoque: Number(evento.target.value) })
        }
        placeholder="Quantidade"
        required
        type="number"
        min={0}
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
      <input
        value={valores.imagem_url ?? ""}
        onChange={(evento) => aoMudar({ ...valores, imagem_url: evento.target.value })}
        placeholder="URL da imagem (opcional)"
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none lg:col-span-2"
      />
    </>
  );
}

export function EstoquePage() {
  const { token } = useAuth();
  const [pecas, setPecas] = useState<Peca[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const [novaPeca, setNovaPeca] = useState<PecaCreateInput>(CAMPOS_VAZIOS);
  const [erroFormulario, setErroFormulario] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [pecaEmEdicao, setPecaEmEdicao] = useState<PecaCreateInput>(CAMPOS_VAZIOS);
  const [erroEdicao, setErroEdicao] = useState<string | null>(null);
  const [salvandoEdicao, setSalvandoEdicao] = useState(false);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);

  function carregarPecas() {
    setCarregando(true);
    listarPecas()
      .then(setPecas)
      .catch(() => setErro("Não foi possível carregar as peças."))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregarPecas();
  }, []);

  async function handleCriar(evento: FormEvent) {
    evento.preventDefault();
    setErroFormulario(null);

    if (!token) {
      setErroFormulario("Faça login novamente para cadastrar peças.");
      return;
    }

    setEnviando(true);
    try {
      await criarPeca(novaPeca, token);
      setNovaPeca(CAMPOS_VAZIOS);
      carregarPecas();
    } catch (erroCapturado) {
      setErroFormulario(
        erroCapturado instanceof Error ? erroCapturado.message : "Erro ao cadastrar peça.",
      );
    } finally {
      setEnviando(false);
    }
  }

  function iniciarEdicao(peca: Peca) {
    setEditandoId(peca.id);
    setPecaEmEdicao(paraFormulario(peca));
    setErroEdicao(null);
  }

  function cancelarEdicao() {
    setEditandoId(null);
    setErroEdicao(null);
  }

  async function salvarEdicao(evento: FormEvent) {
    evento.preventDefault();
    if (!editandoId) return;

    if (!token) {
      setErroEdicao("Faça login novamente para editar peças.");
      return;
    }

    setSalvandoEdicao(true);
    setErroEdicao(null);
    try {
      await atualizarPeca(editandoId, pecaEmEdicao, token);
      setEditandoId(null);
      carregarPecas();
    } catch (erroCapturado) {
      setErroEdicao(
        erroCapturado instanceof Error ? erroCapturado.message : "Erro ao atualizar peça.",
      );
    } finally {
      setSalvandoEdicao(false);
    }
  }

  async function handleExcluir(peca: Peca) {
    if (!token) {
      setErro("Faça login novamente para excluir peças.");
      return;
    }

    const confirmado = window.confirm(`Excluir a peça "${peca.nome}"? Essa ação não pode ser desfeita.`);
    if (!confirmado) return;

    setExcluindoId(peca.id);
    try {
      await excluirPeca(peca.id, token);
      carregarPecas();
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof Error ? erroCapturado.message : "Erro ao excluir peça.");
    } finally {
      setExcluindoId(null);
    }
  }

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Estoque</h2>

      <form
        onSubmit={handleCriar}
        className="mb-8 grid grid-cols-1 gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-6"
      >
        <CamposPeca valores={novaPeca} aoMudar={setNovaPeca} />

        {erroFormulario && (
          <p className="col-span-full text-sm text-red-700">{erroFormulario}</p>
        )}

        <button
          type="submit"
          disabled={enviando}
          className="col-span-full w-fit rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
        >
          {enviando ? "Cadastrando..." : "Cadastrar peça"}
        </button>
      </form>

      {erro && <p className="mb-4 text-sm text-red-700">{erro}</p>}
      {carregando && !erro && <p className="text-sm text-gray-500">Carregando...</p>}

      {!carregando && !erro && pecas.length === 0 && (
        <p className="text-sm text-gray-500">Nenhuma peça cadastrada ainda.</p>
      )}

      {!carregando && !erro && pecas.length > 0 && (
        <div className="flex flex-col gap-3">
          {pecas.map((peca) =>
            editandoId === peca.id ? (
              <form
                key={peca.id}
                onSubmit={salvarEdicao}
                className="grid grid-cols-1 gap-3 rounded-xl border border-[#1a2332] bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-6"
              >
                <CamposPeca valores={pecaEmEdicao} aoMudar={setPecaEmEdicao} />

                {erroEdicao && (
                  <p className="col-span-full text-sm text-red-700">{erroEdicao}</p>
                )}

                <div className="col-span-full flex gap-2">
                  <button
                    type="submit"
                    disabled={salvandoEdicao}
                    className="rounded-lg bg-[#1a2332] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
                  >
                    {salvandoEdicao ? "Salvando..." : "Salvar"}
                  </button>
                  <button
                    type="button"
                    onClick={cancelarEdicao}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            ) : (
              <div
                key={peca.id}
                className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-4 shadow-sm"
              >
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
                </div>

                <div className="text-right text-sm text-gray-600">
                  <p>{formatarPreco(peca.preco)}</p>
                  <p>{peca.quantidade_estoque} em estoque</p>
                </div>

                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => iniciarEdicao(peca)}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                  >
                    Editar
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExcluir(peca)}
                    disabled={excluindoId === peca.id}
                    className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-60"
                  >
                    {excluindoId === peca.id ? "Excluindo..." : "Excluir"}
                  </button>
                </div>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}
