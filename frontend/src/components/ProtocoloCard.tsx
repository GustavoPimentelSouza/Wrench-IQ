import type { Protocolo } from "../types/protocolo";

const CORES_POR_CATEGORIA: Record<string, string> = {
  farol: "bg-sky-100 text-sky-700",
  lanternagem: "bg-amber-100 text-amber-800",
  retirar: "bg-emerald-100 text-emerald-700",
  pintura: "bg-fuchsia-100 text-fuchsia-700",
  funilaria: "bg-orange-100 text-orange-700",
};

const COR_PADRAO = "bg-gray-100 text-gray-700";

interface ProtocoloCardProps {
  protocolo: Protocolo;
}

export function ProtocoloCard({ protocolo }: ProtocoloCardProps) {
  const corBadge = CORES_POR_CATEGORIA[protocolo.categoria] ?? COR_PADRAO;

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      <p className="mb-2 font-medium text-gray-900">
        #{String(protocolo.numero).padStart(4, "0")} · {protocolo.veiculo}
      </p>
      <span
        className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${corBadge}`}
      >
        {protocolo.categoria}
      </span>
    </div>
  );
}
