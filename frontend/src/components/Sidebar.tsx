import { NavLink } from "react-router-dom";

const ITENS_NAVEGACAO = [
  { rota: "/", rotulo: "Painel" },
  { rota: "/protocolos", rotulo: "Protocolos" },
  { rota: "/estoque", rotulo: "Estoque" },
  { rota: "/pedidos", rotulo: "Pedidos" },
  { rota: "/clientes", rotulo: "Clientes" },
  { rota: "/agenda", rotulo: "Agenda" },
];

export function Sidebar() {
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
              `rounded-lg px-4 py-2 text-sm font-medium transition ${
                isActive
                  ? "bg-white/10 text-white"
                  : "text-slate-300 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            {item.rotulo}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
