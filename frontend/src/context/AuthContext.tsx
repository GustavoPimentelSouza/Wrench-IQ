import { createContext, useContext, useState, type ReactNode } from "react";
import type { UsuarioAutenticado } from "../types/auth";

interface AuthContextValue {
  token: string | null;
  usuario: UsuarioAutenticado | null;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function decodificarUsuarioDoToken(token: string): UsuarioAutenticado | null {
  try {
    const payloadBase64 = token.split(".")[1];
    const payloadJson = atob(payloadBase64.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(payloadJson) as { sub: string; papel: string };
    return { id: payload.sub, papel: payload.papel };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [usuario, setUsuario] = useState<UsuarioAutenticado | null>(null);

  function login(novoToken: string) {
    setToken(novoToken);
    setUsuario(decodificarUsuarioDoToken(novoToken));
  }

  function logout() {
    setToken(null);
    setUsuario(null);
  }

  return (
    <AuthContext.Provider value={{ token, usuario, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth precisa ser usado dentro de um AuthProvider");
  }
  return context;
}
