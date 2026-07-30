# Wrench IQ — Frontend

React + TypeScript + TailwindCSS (Vite). Painel de administração da oficina:
login, sidebar de navegação e o Painel principal.

O quadro de protocolos (`PainelPage`), Clientes (CRUD completo + histórico
de serviços), Estoque (CRUD completo) e Pedidos (venda direta de peça, com
o fluxo completo de status) já consomem a API real. Os 3 cards de métrica
no topo do Painel (protocolos abertos, peças com estoque baixo,
faturamento) continuam mockados. Protocolos e Agenda no menu ainda são
placeholders.

## Estrutura

- `src/pages/`: telas (`LoginPage`, `PainelPage`, `ClientesPage`,
  `EstoquePage`, `PedidosPage`, e placeholders de Protocolos/Agenda).
- `src/components/`: peças de UI reutilizáveis (`Sidebar`, `AppLayout`,
  `MetricCard`, `ProtocoloCard`, `ProtectedRoute`).
- `src/services/`: chamadas HTTP à API (`api.ts` define a URL base,
  `authService.ts` faz o login, `protocoloService.ts`/`clienteService.ts`
  listam protocolos e clientes).
- `src/context/`: `AuthContext` — guarda o token JWT **em memória** (state
  do React), não em `localStorage`. Isso significa que dar refresh na página
  desloga o usuário — é intencional por enquanto.
- `src/types/`: tipos TypeScript compartilhados.
- `src/mocks/`: dados ainda mockados dos cards de métrica do Painel.

## Rodando via Docker (recomendado)

Na raiz do projeto (não aqui em `frontend/`):

```
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

O frontend sobe em `http://localhost:3010`. O `docker-compose.local.yml`
monta `src/` e `index.html` como volume, então editar código local reflete
no container sem rebuild (o Vite já faz hot-reload).

Se quiser só o serviço do frontend: `docker compose up -d --build frontend`.

## Rodando localmente com `npm run dev` (fora do Docker)

Útil se preferir rodar sem Docker, ou ter hot-reload mais rápido:

```
cd frontend
npm install
npm run dev
```

Abre em `http://localhost:5173` (porta padrão do Vite fora do Docker).

**Pré-requisito:** a API precisa estar rodando e acessível em
`http://localhost:8010` (o valor padrão de `VITE_API_URL`) — suba pelo menos
`api` e `postgres` via Docker (`docker compose up -d api postgres`), rodando
o frontend localmente ao mesmo tempo.

Para apontar para outra URL de API, crie um `.env` nesta pasta:

```
VITE_API_URL=http://localhost:8010
```

## Por que sempre `localhost:8010`, mesmo em Docker?

As chamadas de API (`fetch`) saem do **navegador**, não de dentro do
container do frontend — então o alvo é sempre a porta exposta pra fora do
Docker (`8010`), nunca o nome interno do serviço (`api:8000`), independente
de o frontend estar rodando em Docker ou local.

## Build de produção

```
npm run build
```

Gera os arquivos estáticos em `dist/` (ainda não há um Dockerfile/nginx de
produção — o Dockerfile atual roda o servidor de desenvolvimento do Vite,
suficiente para este estágio do projeto).
