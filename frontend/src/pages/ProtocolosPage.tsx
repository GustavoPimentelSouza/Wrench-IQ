import { useEffect, useState } from "react";
import { ProtocoloFormulario } from "../components/ProtocoloFormulario";
import { ProtocoloGerenciarLinha } from "../components/ProtocoloGerenciarLinha";
import { listarClientes } from "../services/clienteService";
import { listarProtocolos } from "../services/protocoloService";
import type { Cliente } from "../types/cliente";
import type { Protocolo } from "../types/protocolo";

export function ProtocolosPage() {
  const [protocolos, setProtocolos] = useState<Protocolo[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  function carregarTudo() {
    setCarregando(true);
    Promise.all([listarProtocolos(), listarClientes()])
      .then(([protocolosCarregados, clientesCarregados]) => {
        setProtocolos(protocolosCarregados);
        setClientes(clientesCarregados);
      })
      .catch(() => setErro("Não foi possível carregar os protocolos."))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregarTudo();
  }, []);

  function nomeCliente(clienteId: string): string {
    return clientes.find((c) => c.id === clienteId)?.nome ?? clienteId;
  }

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Protocolos</h2>

      <ProtocoloFormulario clientes={clientes} onCriado={carregarTudo} />

      {erro && <p className="mb-4 text-sm text-red-700">{erro}</p>}
      {carregando && !erro && <p className="text-sm text-gray-500">Carregando...</p>}

      {!carregando && !erro && protocolos.length === 0 && (
        <p className="text-sm text-gray-500">Nenhum protocolo criado ainda.</p>
      )}

      {!carregando && !erro && protocolos.length > 0 && (
        <div className="flex flex-col gap-3">
          {protocolos.map((protocolo) => (
            <ProtocoloGerenciarLinha
              key={protocolo.id}
              protocolo={protocolo}
              nomeCliente={nomeCliente(protocolo.cliente_id)}
              onAtualizado={carregarTudo}
            />
          ))}
        </div>
      )}
    </div>
  );
}
