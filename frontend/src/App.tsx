import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { AgendaPage } from "./pages/AgendaPage";
import { AtendimentoPage } from "./pages/AtendimentoPage";
import { ChatSimuladorPage } from "./pages/ChatSimuladorPage";
import { ClientesPage } from "./pages/ClientesPage";
import { ConfiguracoesPage } from "./pages/ConfiguracoesPage";
import { EstoquePage } from "./pages/EstoquePage";
import { LoginPage } from "./pages/LoginPage";
import { PainelPage } from "./pages/PainelPage";
import { PedidosPage } from "./pages/PedidosPage";
import { ProtocolosPage } from "./pages/ProtocolosPage";

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index element={<PainelPage />} />
            <Route path="/protocolos" element={<ProtocolosPage />} />
            <Route path="/estoque" element={<EstoquePage />} />
            <Route path="/pedidos" element={<PedidosPage />} />
            <Route path="/clientes" element={<ClientesPage />} />
            <Route path="/agenda" element={<AgendaPage />} />
            <Route path="/simulador" element={<ChatSimuladorPage />} />
            <Route path="/atendimento" element={<AtendimentoPage />} />
            <Route path="/configuracoes" element={<ConfiguracoesPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
