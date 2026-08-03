import { createContext, useContext, useState, type ReactNode } from "react";
import type { UsuarioAutenticado } from "../types/auth";

interface AuthContextValue {
  token: string | null;
  usuario: UsuarioAutenticado | null;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const CHAVE_TOKEN = "wrenchiq_token";

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
  // Lido de localStorage na inicialização — sem isso, todo F5 desloga,
  // mesmo com o token ainda válido.
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(CHAVE_TOKEN));
  const [usuario, setUsuario] = useState<UsuarioAutenticado | null>(() => {
    const tokenSalvo = localStorage.getItem(CHAVE_TOKEN);
    return tokenSalvo ? decodificarUsuarioDoToken(tokenSalvo) : null;
  });

  function login(novoToken: string) {
    localStorage.setItem(CHAVE_TOKEN, novoToken);
    setToken(novoToken);
    setUsuario(decodificarUsuarioDoToken(novoToken));
  }

  function logout() {
    localStorage.removeItem(CHAVE_TOKEN);
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
