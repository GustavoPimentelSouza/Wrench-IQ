// As chamadas de API saem do navegador do usuário, não de dentro do container
// do frontend — por isso o alvo é sempre "localhost:8010" (a porta da API
// exposta para fora do Docker), nunca o nome do serviço interno ("api:8000"),
// mesmo quando o frontend também roda em Docker.
export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8010";
