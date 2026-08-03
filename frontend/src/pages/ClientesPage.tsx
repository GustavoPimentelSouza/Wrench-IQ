import { useEffect, useState } from "react";
import { ClienteFormulario } from "../components/ClienteFormulario";
import { ClienteLinha } from "../components/ClienteLinha";
import { listarClientes } from "../services/clienteService";
import type { Cliente } from "../types/cliente";

export function ClientesPage() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  function carregarClientes() {
    setCarregando(true);
    listarClientes()
      .then(setClientes)
      .catch(() => setErro("Não foi possível carregar os clientes."))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregarClientes();
  }, []);

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Clientes</h2>

      <ClienteFormulario onCriado={carregarClientes} />

      {erro && <p className="mb-4 text-sm text-red-700">{erro}</p>}
      {carregando && !erro && <p className="text-sm text-gray-500">Carregando...</p>}

      {!carregando && !erro && clientes.length === 0 && (
        <p className="text-sm text-gray-500">Nenhum cliente cadastrado ainda.</p>
      )}

      {!carregando && !erro && clientes.length > 0 && (
        <div className="flex flex-col gap-3">
          {clientes.map((cliente) => (
            <ClienteLinha key={cliente.id} cliente={cliente} onAtualizado={carregarClientes} />
          ))}
        </div>
      )}
    </div>
  );
}
