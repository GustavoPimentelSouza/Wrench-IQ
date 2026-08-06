import type { PecaCreateInput } from "../types/peca";

interface CamposPecaProps {
  valores: PecaCreateInput;
  aoMudar: (valores: PecaCreateInput) => void;
}

export function CamposPeca({ valores, aoMudar }: CamposPecaProps) {
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
        value={valores.cor ?? ""}
        onChange={(evento) => aoMudar({ ...valores, cor: evento.target.value })}
        placeholder="Cor (opcional — deixe em branco se a peça não varia por cor)"
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
