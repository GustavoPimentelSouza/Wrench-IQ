import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { listarAtendimentoPendente } from "../services/atendimentoService";

const ITENS_NAVEGACAO = [
  { rota: "/", rotulo: "Painel" },
  { rota: "/protocolos", rotulo: "Protocolos" },
  { rota: "/estoque", rotulo: "Estoque" },
  { rota: "/pedidos", rotulo: "Pedidos" },
  { rota: "/clientes", rotulo: "Clientes" },
  { rota: "/agenda", rotulo: "Agenda" },
  { rota: "/simulador", rotulo: "Simulador (IA)" },
  { rota: "/atendimento", rotulo: "Atendimento" },
  { rota: "/configuracoes", rotulo: "Configurações" },
];

export function Sidebar() {
  const { token } = useAuth();
  const [pendentes, setPendentes] = useState(0);

  // Só busca uma vez ao carregar a tela (sem polling) — o objetivo aqui é
  // o atendente notar que tem algo esperando sem precisar entrar na tela,
  // não um contador em tempo real; abrir/fechar a aba já atualiza.
  useEffect(() => {
    if (!token) return;
    listarAtendimentoPendente(token)
      .then((lista) => setPendentes(lista.length))
      .catch(() => undefined);
  }, [token]);

  return (
    <aside className="flex w-64 shrink-0 flex-col bg-[#1a2332] px-4 py-6">
      <h1 className="mb-8 px-2 text-xl font-semibold text-white">Wrench IQ</h1>
      <nav className="flex flex-col gap-1">
        {ITENS_NAVEGACAO.map((item) => (
          <NavLink
            key={item.rota}
            to={item.rota}
            end={item.rota === "/"}
            className={({ isActive }) =>
              `flex items-center justify-between rounded-lg px-4 py-2 text-sm font-medium transition ${
                isActive
                  ? "bg-white/10 text-white"
                  : "text-slate-300 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <span>{item.rotulo}</span>
            {item.rota === "/atendimento" && pendentes > 0 && (
              <span className="rounded-full bg-red-600 px-2 py-0.5 text-xs font-semibold text-white">
                {pendentes}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
