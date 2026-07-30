import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { CredenciaisInvalidasError, login as loginRequest } from "../services/authService";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setCarregando(true);

    try {
      const resposta = await loginRequest({ email, senha });
      login(resposta.access_token);
      navigate("/", { replace: true });
    } catch (erroCapturado) {
      if (erroCapturado instanceof CredenciaisInvalidasError) {
        setErro(erroCapturado.message);
      } else {
        setErro("Não foi possível conectar ao servidor.");
      }
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm"
      >
        <h1 className="mb-6 text-2xl font-semibold text-[#1a2332]">Wrench IQ</h1>

        {erro && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">
            {erro}
          </div>
        )}

        <label className="mb-1 block text-sm font-medium text-gray-600" htmlFor="email">
          E-mail
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(evento) => setEmail(evento.target.value)}
          required
          className="mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-[#1a2332] focus:outline-none"
        />

        <label className="mb-1 block text-sm font-medium text-gray-600" htmlFor="senha">
          Senha
        </label>
        <input
          id="senha"
          type="password"
          value={senha}
          onChange={(evento) => setSenha(evento.target.value)}
          required
          className="mb-6 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-[#1a2332] focus:outline-none"
        />

        <button
          type="submit"
          disabled={carregando}
          className="w-full rounded-lg bg-[#1a2332] py-2 font-medium text-white transition hover:bg-[#243044] disabled:opacity-60"
        >
          {carregando ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}
