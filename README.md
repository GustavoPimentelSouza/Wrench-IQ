# Wrench IQ

Etapa atual: modelos de `Peca`, `Usuario`, `Mensagem`, `Protocolo`,
`Cliente` e `Pedido` (venda direta de peça) com persistência em Postgres via
SQLAlchemy assíncrono + Alembic, seguindo Clean Architecture, mais um painel
administrativo (SQLAdmin) em `/admin` e um assistente de IA via tool calling
(consulta de peça, criação de pedido) com busca semântica (`pgvector`).
WhatsApp de verdade (Evolution API) ainda não está integrado — de propósito,
por enquanto.

## Comandos do dia a dia

Essa seção é só isso: o comando, quando usar, e por quê. Pra referência de
endpoints da API, veja "Endpoints" mais abaixo.

### Subir o projeto
```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
```
Use esse na maioria das vezes — sobe API, frontend, Postgres e pgAdmin,
reaproveitando as imagens já existentes.

### Subir com rebuild
```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```
Só quando `requirements.txt`, `frontend/package.json` ou algum `Dockerfile`
mudar. Código Python/TypeScript puro recarrega sozinho (hot-reload) — rebuild
sem necessidade só acumula imagem órfã e gasta espaço em disco à toa.

### Parar o projeto
```bash
docker compose down
```
Derruba os containers, mas preserva os dados do banco (volume
`wrenchiq_postgres_data`). Nunca use `-v` a menos que queira apagar o banco
de propósito.

### Aplicar migração nova
```bash
docker exec wrenchiq_api alembic upgrade head
```
Roda toda vez que aparecer um arquivo novo em `alembic/versions/` (uma
coluna ou tabela nova). Sem isso, a API sobe normalmente mas quebra assim
que tentar usar algo que ainda não existe no banco.

### Rodar os testes
```bash
source venv/bin/activate
pytest
```
Roda contra o banco `wrenchiq_test` — separado do banco de desenvolvimento
(configurado em `.env.test`), e é limpo automaticamente antes e depois de
cada rodada (ver `tests/conftest.py`). Nunca suja o que aparece no
painel/site de verdade.

### Limpar imagem Docker órfã
```bash
docker image prune -f
```
Só remove imagem sem uso (não afeta outros projetos Docker na mesma
máquina) — vale rodar de vez em quando depois de um `--build`, se o espaço
em disco for curto.

## Estrutura

- `domain/`: entidades puras (`Peca`, `Usuario`, `Mensagem`, `Protocolo`,
  `Cliente`, `Pedido`), sem dependência de framework.
- `application/`: casos de uso e as portas de repositório (`PecaUseCases`,
  `ProtocoloUseCases`, `ClienteUseCases`, etc.).
- `adapters/`: implementação concreta com SQLAlchemy (`PecaORM`,
  `UsuarioORM`, `ProtocoloORM`, `ClienteORM`, `SqlAlchemyPecaRepository`
  e equivalentes).
- `infrastructure/`: conexão com banco, config, routers FastAPI e o painel
  administrativo (`admin.py`).
- `alembic/`: migrações do schema.
- `frontend/`: painel web (React + TypeScript + TailwindCSS) — veja
  `frontend/README.md` para detalhes de como rodar.

`Usuario` tem autenticação JWT própria (`/auth/login`, `/auth/registrar`) —
veja a seção "Autenticação (JWT)". A gestão manual de peças/usuários sem
passar pela API continua disponível pelo painel `/admin`.

## Arquivos Docker

- `docker-compose.yml`: definição base dos serviços (`api`, `frontend`,
  `postgres`).
- `docker-compose.local.yml`: override de desenvolvimento — hot-reload do
  FastAPI (`--reload`) e montagem do código local como volume.

## Como rodar (desenvolvimento)

```
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

Ao subir, o container roda `alembic upgrade head` automaticamente antes de
iniciar o servidor, aplicando as migrações (tabelas `pecas`, `usuarios`,
`mensagens`, `protocolos`, `clientes`, `pedidos` — `cliente_id`/`peca_id`
são FKs de verdade em todas as tabelas relacionadas, com `RESTRICT` contra
exclusão que perderia histórico).

A API sobe em `http://localhost:8010`, o frontend em `http://localhost:3011`.
O Postgres (imagem `pgvector/pgvector:pg15`) sobe junto na porta `5433`.

Login inicial do painel web (semeado pela migração `0004`, mesmas
credenciais do `/auth/login` — veja "Autenticação (JWT)"):

- e-mail: `admin@wrenchiq.com`
- senha: `admin123`

Containers e rede usam o prefixo `wrenchiq_` para não conflitar com outros
projetos Docker rodando na mesma máquina.

## Endpoints

### `POST /webhook`

Simula o recebimento de uma mensagem (ainda sem Evolution API/WhatsApp de
verdade — só a "porta de entrada" simulada). Resolve o `Cliente` pelo
`telefone` (cria um novo automaticamente se não existir), classifica e
persiste a mensagem via o mesmo pipeline de `/mensagens`.

```
curl -X POST http://localhost:8010/webhook \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511999999999", "mensagem": "Qual o preço do farol?"}'
```

### `/pecas`

`POST`, `PUT` e `DELETE` exigem um token JWT (veja "Autenticação (JWT)"
abaixo); `GET` continua público.

```
# criar (autenticado)
curl -X POST http://localhost:8010/pecas \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"nome": "Pastilha de freio", "marca_modelo_compativel": "Honda CG 160", "ano_compativel": "2020-2024", "preco": "89.90", "quantidade_estoque": 10}'

# listar (público)
curl http://localhost:8010/pecas

# buscar uma (público)
curl http://localhost:8010/pecas/{id}

# atualizar (autenticado)
curl -X PUT http://localhost:8010/pecas/{id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"nome": "Pastilha de freio", "marca_modelo_compativel": "Honda CG 160", "ano_compativel": "2020-2024", "preco": "79.90", "quantidade_estoque": 8}'

# excluir (autenticado)
curl -X DELETE http://localhost:8010/pecas/{id} \
  -H "Authorization: Bearer $TOKEN"
```

### `/protocolos`

Mesma convenção: `GET` público, `POST`/`PUT`/`DELETE` exigem token. O campo
`numero` é sequencial, gerado pelo banco (não enviar no corpo da requisição).

```
# criar (autenticado)
curl -X POST http://localhost:8010/protocolos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"cliente_id": "cliente-1", "veiculo": "Onix 2022", "categoria": "farol", "status": "em_execucao"}'

# listar (público) — é o que o Painel do frontend consome
curl http://localhost:8010/protocolos
```

### `/clientes`

Mesma convenção: `GET` público, `POST`/`PUT`/`DELETE` exigem token.
`telefone` é único — é o identificador que vai ser usado quando o WhatsApp
for integrado. Validado no formato de número com DDI: só dígitos, entre 10
e 15 caracteres (ex: `5511999999999`) — não aceita mais quantidade
ilimitada de dígitos.

```
# criar (autenticado)
curl -X POST http://localhost:8010/clientes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"nome": "Fulano da Silva", "telefone": "5599999999999", "email": "fulano@exemplo.com"}'

# listar (público) — é o que a tela Clientes do frontend consome
curl http://localhost:8010/clientes
```

### `/pedidos` (venda direta de peça)

Diferente de `/pecas`/`/protocolos`, **todos** os endpoints exigem token
(dados de pagamento/endereço são mais sensíveis que catálogo). Preço nunca
é aceito do cliente — sempre calculado a partir do `Peca.preco` real no
banco. Link de pagamento (`link_pagamento`) é **mockado** por enquanto
(`adapters/pagamento.py`) — sem integração real com gateway ainda.

Fluxo:
- `retirada_local` → `aguardando_retirada` → (staff confirma) `entregue`.
- `envio_remoto` → `aguardando_pagamento` → (confirma pagamento)
  `aguardando_conferencia` → (confirma conferência, "um clique", nunca pula
  essa etapa) `despachado` → (confirma entrega) `entregue`.
- Qualquer pedido não finalizado pode ser `cancelado` — devolve a
  quantidade ao estoque automaticamente.
- `dentro_do_prazo_arrependimento` (7 dias, CDC) é calculado na resposta
  a partir de `entregue_em`, só para `envio_remoto`.

```
# criar pedido (envio remoto)
curl -X POST http://localhost:8010/pedidos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"cliente_id": "<uuid-do-cliente>", "peca_id": "<uuid-da-peca>", "quantidade": 1, "tipo_entrega": "envio_remoto", "endereco_entrega": "Rua Exemplo, 123"}'

# avançar o fluxo
curl -X POST http://localhost:8010/pedidos/{id}/confirmar-pagamento -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8010/pedidos/{id}/confirmar-conferencia -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8010/pedidos/{id}/marcar-entregue -H "Authorization: Bearer $TOKEN"

# cancelar (restaura estoque)
curl -X POST http://localhost:8010/pedidos/{id}/cancelar -H "Authorization: Bearer $TOKEN"
```

## Autenticação (JWT)

A migração `0004` já semeia um usuário admin inicial (necessário porque
`/auth/registrar` exige um admin logado — sem esse "usuário zero", ninguém
conseguiria criar o primeiro usuário):

- e-mail: `admin@wrenchiq.com`
- senha: `admin123`

**Importante:** essas credenciais e o `JWT_SECRET_KEY` (`docker-compose.yml`)
são apenas para desenvolvimento. Troque a senha do admin e o `JWT_SECRET_KEY`
antes de qualquer uso além do ambiente local.

```
# login — retorna o token JWT
TOKEN=$(curl -s -X POST http://localhost:8010/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@wrenchiq.com", "senha": "admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# registrar novo usuário (atendente/mecanico) — exige token de admin
curl -X POST http://localhost:8010/auth/registrar \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"nome": "Fulano", "email": "fulano@wrenchiq.com", "senha": "senha123", "papel": "atendente"}'
```

O token contém o `id` (claim `sub`) e o `papel` do usuário, expira em
`JWT_EXPIRA_MINUTOS` (padrão 60 min), e é validado pela dependência
`get_current_user` (`infrastructure/security_dependencies.py`) via header
`Authorization: Bearer <token>`.

## Painel administrativo (`/admin`)

Acesse `http://localhost:8010/admin` para gerenciar `Peça` e `Usuário`
(criar/editar/excluir) sem precisar de frontend customizado.

Login padrão de desenvolvimento (definido em `docker-compose.yml`):

- usuário: `admin`
- senha: `admin`

**Importante:** essas credenciais e o `ADMIN_SECRET_KEY` são apenas para
desenvolvimento local. Em produção, defina `ADMIN_USER`, `ADMIN_PASSWORD` e
`ADMIN_SECRET_KEY` com valores fortes via variáveis de ambiente/secrets —
nunca deixe os valores padrão.

## Visualizar dados (pgAdmin)

O `docker-compose.local.yml` sobe também um pgAdmin em
`http://localhost:5050`, já com a conexão para o `wrenchiq_postgres`
pré-cadastrada (`pgadmin/servers.json`).

1. Login do pgAdmin (não é a senha do banco):
   - e-mail: `admin@wrenchiq.com`
   - senha: `admin`
2. No painel esquerdo, abra o servidor **"Wrench IQ - Postgres"**.
3. Quando pedir a senha da conexão, use a senha do Postgres: `wrenchiq`.

**Importante:** credenciais de desenvolvimento apenas — não expor essa
configuração em produção.

## Testes

Os testes usam o banco definido em `DATABASE_URL_TEST` — um banco **separado**
do de desenvolvimento (`wrenchiq_test`, não `wrenchiq`), no mesmo Postgres
(`wrenchiq_postgres`). Isso existe porque, sem isolamento, cada rodada de
`pytest` cria Cliente/Peça/Usuário/Mensagem de teste que vazavam direto pro
banco que o painel web mostra. `tests/conftest.py` também limpa todas as
tabelas (menos o usuário admin semeado) antes e depois de cada rodada — o
banco de teste começa e termina vazio sempre.

Se for a primeira vez rodando, o banco `wrenchiq_test` precisa existir e ter
as migrações aplicadas:
```bash
docker exec wrenchiq_postgres psql -U wrenchiq -d wrenchiq -c "CREATE DATABASE wrenchiq_test"
DB_HOST=localhost DB_PORT=5433 DB_NAME=wrenchiq_test alembic upgrade head
```

Testes que envolvem `/mensagens`/`/webhook` usam fakes (`tests/fakes.py`) no
lugar da IA real (Groq/Gemini) — sem custo, sem chave de API, sem rede. Isso
é feito sobrescrevendo `infrastructure.ia.get_classificador`,
`get_chat_service` e `get_embedding_service` em `tests/conftest.py`. Existe
**um** teste que chama o Groq de verdade (`tests/test_groq_integracao_real.py`),
marcado `@pytest.mark.integracao_real` e **excluído do `pytest` padrão** (via
`addopts` em `pytest.ini`). Pra validar a integração de fato (precisa de
`GROQ_API_KEY` configurada):

```
pytest -m integracao_real -o addopts="" tests/test_groq_integracao_real.py
```

### 1) Rodando dentro do container

```
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
docker compose exec api pytest --cov
```

### 2) Rodando localmente (fora do Docker), com o Test Explorer do VS Code

Pré-requisito: o Postgres precisa estar acessível em `localhost:5433` (basta
rodar `docker compose up -d postgres` ou subir a stack completa uma vez para
aplicar as migrações).

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest --cov
```

No VS Code, abra a paleta de comandos e rode **"Python: Configure Tests"**
(ou **"Configure Python Tests"**), escolha **pytest** e o diretório `tests`.
O arquivo `.vscode/settings.json` já vem com essa configuração pronta, então
o Test Explorer deve detectar os testes automaticamente ao selecionar o
interpretador do `venv/`.
