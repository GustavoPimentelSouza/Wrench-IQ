import { useEffect, useState } from "react";
import { PecaFormulario } from "../components/PecaFormulario";
import { PecaLinha } from "../components/PecaLinha";
import { listarPecas } from "../services/pecaService";
import type { Peca } from "../types/peca";

export function EstoquePage() {
  const [pecas, setPecas] = useState<Peca[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

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

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Estoque</h2>

      <PecaFormulario onCriada={carregarPecas} />

      {erro && <p className="mb-4 text-sm text-red-700">{erro}</p>}
      {carregando && !erro && <p className="text-sm text-gray-500">Carregando...</p>}

      {!carregando && !erro && pecas.length === 0 && (
        <p className="text-sm text-gray-500">Nenhuma peça cadastrada ainda.</p>
      )}

      {!carregando && !erro && pecas.length > 0 && (
        <div className="flex flex-col gap-3">
          {pecas.map((peca) => (
            <PecaLinha key={peca.id} peca={peca} onAtualizada={carregarPecas} />
          ))}
        </div>
      )}
    </div>
  );
}
