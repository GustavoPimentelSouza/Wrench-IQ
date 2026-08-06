import type { ClienteCreateInput } from "../types/cliente";

interface CamposClienteProps {
  valores: ClienteCreateInput;
  aoMudar: (valores: ClienteCreateInput) => void;
}

export function CamposCliente({ valores, aoMudar }: CamposClienteProps) {
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
        value={valores.telefone}
        onChange={(evento) => aoMudar({ ...valores, telefone: evento.target.value })}
        placeholder="Telefone com DDI, só números (ex: 5511999999999)"
        pattern="\d{10,15}"
        maxLength={15}
        required
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
      <input
        value={valores.email ?? ""}
        onChange={(evento) => aoMudar({ ...valores, email: evento.target.value })}
        placeholder="E-mail (opcional)"
        type="email"
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none"
      />
      <input
        value={valores.endereco ?? ""}
        onChange={(evento) => aoMudar({ ...valores, endereco: evento.target.value })}
        placeholder="Endereço (opcional)"
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1a2332] focus:outline-none sm:col-span-2"
      />
    </>
  );
}
